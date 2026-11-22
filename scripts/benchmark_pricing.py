"""Run isolated local-pricing or explicitly authorized LLM-pricing benchmarks."""

from __future__ import annotations

import argparse
import csv
import sys
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

from grocery_store_interface import using_grocery_pricing_mode
from grocery_store_interface.errors import GroceryPricingError
from grocery_store_interface.models import IngredientRequirement
from llm_api_interface import request_pricing
from llm_api_interface.errors import RecipeGenerationServiceError
from llm_api_interface.pricing_estimator import (
    PricingBenchmarkError,
    build_pricing_request,
    create_pricing_client,
    request_price_estimates,
    validate_price_estimates,
)
from pricing_timing import (
    ExternalRequestBudget,
    ExternalRequestBudgetExceeded,
    PricingMeasurement,
    activate_measurement,
    activate_request_budget,
    measure_stage,
)
from recipe_service import (
    calculate_recipe_costs,
    identify_owned_recipe_ingredients,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
CHAPTER10_RESULTS_DIR = ROOT_DIR / "results" / "chapter10-4"
CHAPTER11_RESULTS_DIR = ROOT_DIR / "results" / "chapter11"
CHAPTER10_INPUT_DATASET_ID = "chapter10-five-ingredient-names-v1"
CHAPTER11_INPUT_DATASET_ID = "chapter11-five-ingredient-requirements-v1"
BENCHMARK_INGREDIENTS = (
    "chicken",
    "rice",
    "broccoli",
    "olive oil",
    "garlic",
)
BENCHMARK_REQUIREMENTS: tuple[IngredientRequirement, ...] = (
    {"name": "chicken", "quantity": 16.0, "unit": "oz"},
    {"name": "rice", "quantity": 16.0, "unit": "oz"},
    {"name": "broccoli", "quantity": 1.0, "unit": "head"},
    {"name": "olive oil", "quantity": 1.0, "unit": "fl_oz"},
    {"name": "garlic", "quantity": 1.0, "unit": "bulb"},
)
MAX_LIVE_REQUESTS = 30
MAX_KROGER_HTTP_REQUESTS = 180
BENCHMARK_BUDGET = 1_000_000.0
CSV_FIELDS = [
    "run_id",
    "timestamp_utc",
    "scenario",
    "mode",
    "model",
    "input_dataset_id",
    "stage",
    "duration_ns",
    "status",
    "run_status",
    "attempt_number",
    "attempt_count",
    "retry_attempts",
    "provider_request_count",
    "error_type",
    "provider_status_code",
]


def _run_local_pricing(measurement: PricingMeasurement) -> None:
    _run_pricing_workflow(measurement, mode="stub")


def _run_html_fixture_pricing(measurement: PricingMeasurement) -> None:
    _run_pricing_workflow(measurement, mode="html_fixture")


def _run_kroger_pricing(measurement: PricingMeasurement) -> None:
    _run_pricing_workflow(measurement, mode="kroger")


def _run_pricing_workflow(
    measurement: PricingMeasurement,
    *,
    mode: str,
) -> None:
    recipes = [
        {
            "name": "Chapter 11 pricing benchmark",
            "ingredients": [dict(item) for item in BENCHMARK_REQUIREMENTS],
        }
    ]
    with using_grocery_pricing_mode(mode), activate_measurement(measurement):
        with measurement.measure("pricing_workflow_total"):
            recipes_with_pricing = request_pricing(recipes)
            for recipe in recipes_with_pricing:
                _process_priced_ingredients(
                    list(recipe["ingredients"].items())
                )
    measurement.mark_success()


def _run_llm_pricing(measurement: PricingMeasurement) -> None:
    ingredients = list(BENCHMARK_INGREDIENTS)
    with activate_measurement(measurement):
        with measurement.measure("pricing_workflow_total"):
            with measurement.measure("llm_request_total"):
                with measurement.measure("llm_client_setup"):
                    client, model = create_pricing_client()
                    measurement.model = model
                with measure_stage("llm_request_preparation"):
                    request_input = build_pricing_request(ingredients)
                with measurement.measure_attempt():
                    output_text = request_price_estimates(
                        client,
                        model,
                        request_input,
                    )
            with measurement.measure("pricing_response_validation"):
                estimates = validate_price_estimates(output_text, ingredients)
            _process_priced_ingredients(
                [
                    (
                        estimate["ingredient"],
                        estimate["estimated_price_usd"],
                    )
                    for estimate in estimates
                ]
            )
    measurement.mark_success()


def _process_priced_ingredients(
    ingredient_items: list[tuple[str, float]],
) -> None:
    names = [name for name, _price in ingredient_items]
    ownership = identify_owned_recipe_ingredients(names, [])
    priced_ingredients = [
        {
            "name": name,
            "estimated_price": price,
            "owned": is_owned,
        }
        for (name, price), is_owned in zip(
            ingredient_items,
            ownership,
            strict=True,
        )
    ]
    calculate_recipe_costs(
        priced_ingredients,
        budget=BENCHMARK_BUDGET,
    )


def _measurement_rows(measurement: PricingMeasurement) -> list[dict[str, object]]:
    return [
        {
            "run_id": measurement.run_id,
            "timestamp_utc": measurement.timestamp_utc,
            "scenario": measurement.scenario,
            "mode": measurement.mode,
            "model": measurement.model,
            "input_dataset_id": measurement.input_dataset_id,
            "stage": timing.stage,
            "duration_ns": timing.duration_ns,
            "status": timing.status,
            "run_status": measurement.run_status,
            "attempt_number": timing.attempt_number,
            "attempt_count": measurement.attempt_count,
            "retry_attempts": measurement.retry_attempts,
            "provider_request_count": measurement.provider_request_count,
            "error_type": timing.error_type,
            "provider_status_code": measurement.provider_status_code,
        }
        for timing in measurement.stage_timings
    ]


def _default_output_path(mode: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_dir = (
        CHAPTER10_RESULTS_DIR if mode == "llm" else CHAPTER11_RESULTS_DIR
    )
    return results_dir / f"{mode}-pricing-{timestamp}.csv"


def _confirm_live_run(mode: str, run_count: int, max_requests: int) -> bool:
    phrase = (
        f"RUN {run_count} {mode.upper()} PRICING RUNS "
        f"WITH CAP {max_requests}"
    )
    if mode == "llm":
        print(
            "This experiment sends one pricing request per run to OpenAI. "
            "SDK retries are disabled; charges may apply."
        )
    else:
        print(
            "This experiment calls Kroger's Products API. Each fixed-basket "
            "workflow can send up to one OAuth request and five product "
            "searches. Requests are paced; no automatic retry is performed."
        )
    return input(f"Type '{phrase}' to continue: ").strip() == phrase


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark local dictionary, HTML fixture, Kroger API, or "
            "experimental LLM pricing."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("local", "html-fixture", "kroger", "llm"),
        required=True,
        help=(
            "local measures the in-memory dictionary; html-fixture measures "
            "saved local HTML; kroger and llm require --live."
        ),
    )
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument(
        "--max-requests",
        type=int,
        help=(
            "Per-invocation cap for external HTTP requests (LLM or Kroger)."
        ),
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly opt into external pricing requests.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="For live LLM mode, continue after a failed run without retrying.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="CSV output path; existing files are never overwritten.",
    )
    args = parser.parse_args(argv)

    if args.runs < 1:
        parser.error("--runs must be greater than zero.")
    if args.mode in {"llm", "kroger"}:
        if not args.live:
            parser.error("Live pricing modes require the explicit --live flag.")
        if args.max_requests is None:
            parser.error("Live pricing requires an explicit --max-requests cap.")
        max_cap = (
            MAX_LIVE_REQUESTS
            if args.mode == "llm"
            else MAX_KROGER_HTTP_REQUESTS
        )
        if not 1 <= args.max_requests <= max_cap:
            parser.error(
                f"--max-requests must be between 1 and {max_cap}."
            )
        if args.runs > MAX_LIVE_REQUESTS:
            parser.error(f"Live runs cannot exceed {MAX_LIVE_REQUESTS}.")
        if args.mode == "llm" and args.runs > args.max_requests:
            parser.error("--runs cannot exceed --max-requests for LLM mode.")
        if args.mode == "kroger" and args.max_requests < args.runs:
            parser.error(
                "--max-requests must allow at least one request per run."
            )
        if args.mode == "kroger" and args.continue_on_error:
            parser.error(
                "--continue-on-error is not supported for Kroger benchmark runs."
            )
    else:
        if args.live:
            parser.error("--live is valid only with --mode kroger or llm.")
        if args.continue_on_error:
            parser.error(
                "--continue-on-error is valid only with --mode llm."
            )
        if args.max_requests is not None and args.runs > args.max_requests:
            parser.error("--runs cannot exceed --max-requests.")

    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.mode in {"llm", "kroger"} and not _confirm_live_run(
        args.mode,
        args.runs,
        args.max_requests,
    ):
        print("Live pricing benchmark cancelled; no request was sent.")
        return 2

    output_path = (args.output or _default_output_path(args.mode)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_file = output_path.open(
            "x",
            newline="",
            encoding="utf-8",
        )
    except FileExistsError:
        print(
            f"Refusing to overwrite existing benchmark output: {output_path}",
            file=sys.stderr,
        )
        return 2

    failed_runs = 0
    request_budget = (
        ExternalRequestBudget(args.max_requests)
        if args.mode in {"llm", "kroger"}
        else None
    )
    budget_context = (
        activate_request_budget(request_budget)
        if request_budget is not None
        else nullcontext()
    )
    with output_file, budget_context:
        writer = csv.DictWriter(output_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for run_number in range(1, args.runs + 1):
            scenario = (
                "actual_in_memory_dictionary"
                if args.mode == "local"
                else "actual_html_fixture_pricing"
                if args.mode == "html-fixture"
                else "actual_kroger_api_pricing"
                if args.mode == "kroger"
                else "experimental_llm_pricing"
            )
            measurement = PricingMeasurement(
                scenario=scenario,
                mode=args.mode.replace("-", "_"),
                input_dataset_id=(
                    CHAPTER10_INPUT_DATASET_ID
                    if args.mode == "llm"
                    else CHAPTER11_INPUT_DATASET_ID
                ),
            )
            try:
                if args.mode == "local":
                    _run_local_pricing(measurement)
                elif args.mode == "html-fixture":
                    _run_html_fixture_pricing(measurement)
                elif args.mode == "llm":
                    _run_llm_pricing(measurement)
                elif args.mode == "kroger":
                    _run_kroger_pricing(measurement)
            except (
                ExternalRequestBudgetExceeded,
                GroceryPricingError,
                PricingBenchmarkError,
                RecipeGenerationServiceError,
            ) as error:
                measurement.mark_failure(
                    error,
                    provider_status_code=getattr(
                        error,
                        "provider_status_code",
                        None,
                    ),
                )
                failed_runs += 1
            except Exception as error:
                measurement.mark_failure(error)
                _write_measurement(writer, output_file, measurement)
                print(
                    f"Run {run_number} stopped after "
                    f"{measurement.failure_type}; see {output_path}",
                    file=sys.stderr,
                )
                raise

            _write_measurement(writer, output_file, measurement)
            print(
                f"Run {run_number}/{args.runs}: {measurement.run_status}; "
                f"run_id={measurement.run_id}; "
                f"attempts={measurement.attempt_count}; "
                f"retries={measurement.retry_attempts}; "
                f"provider_requests={measurement.provider_request_count}"
            )
            if (
                args.mode in {"llm", "kroger"}
                and measurement.run_status == "failure"
                and not args.continue_on_error
            ):
                print(
                    "Stopping after the first failed live run; "
                    "use --continue-on-error only if additional requests "
                    "are approved.",
                    file=sys.stderr,
                )
                break

        output_file.flush()

    print(f"Timing CSV written to {output_path}")
    return 1 if failed_runs else 0


def _write_measurement(
    writer: csv.DictWriter,
    output_file,
    measurement: PricingMeasurement,
) -> None:
    writer.writerows(_measurement_rows(measurement))
    output_file.flush()


if __name__ == "__main__":
    raise SystemExit(main())
