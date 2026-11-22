import csv
import io
import json
from types import SimpleNamespace

import pytest
from openai import OpenAIError

import llm_api_interface
from llm_api_interface import pricing_estimator
from llm_api_interface.pricing_estimator import PricingBenchmarkError
from pricing_timing import (
    ExternalRequestBudget,
    ExternalRequestBudgetExceeded,
    PricingMeasurement,
    activate_measurement,
    activate_request_budget,
    measure_stage,
    record_external_request,
)
from recipe_service import (
    calculate_recipe_costs,
    identify_owned_recipe_ingredients,
)
from scripts import analyze_pricing_benchmark, benchmark_pricing


_INGREDIENTS = ["chicken", "rice", "broccoli", "olive oil", "garlic"]
_VALID_PRICES = json.dumps(
    {
        "prices": [
            {"ingredient": "chicken", "estimated_price_usd": 4.5},
            {"ingredient": "rice", "estimated_price_usd": 2.0},
            {"ingredient": "broccoli", "estimated_price_usd": 2.49},
            {"ingredient": "olive oil", "estimated_price_usd": 7.25},
            {"ingredient": "garlic", "estimated_price_usd": 0.75},
        ]
    }
)


def test_timing_context_records_duration_and_failure_without_swallowing(
    monkeypatch,
):
    ticks = iter([100, 145, 200, 275])
    monkeypatch.setattr("pricing_timing.perf_counter_ns", lambda: next(ticks))
    measurement = PricingMeasurement("test", "local", "fixture")

    with measurement.measure("successful_stage"):
        pass
    with pytest.raises(ValueError):
        with measurement.measure("failed_stage"):
            raise ValueError("private detail")

    assert [
        (timing.stage, timing.duration_ns, timing.status, timing.error_type)
        for timing in measurement.stage_timings
    ] == [
        ("successful_stage", 45, "success", ""),
        ("failed_stage", 75, "failure", "ValueError"),
    ]


def test_existing_pricing_functions_emit_opt_in_stage_timings(capsys):
    measurement = PricingMeasurement(
        "actual_in_memory_dictionary",
        "local",
        "test",
    )
    recipes = [
        {
            "name": "Benchmark",
            "ingredients": [
                {
                    "name": name,
                    "quantity": 1.0,
                    "unit": "count",
                }
                for name in _INGREDIENTS
            ],
        }
    ]

    with activate_measurement(measurement):
        priced_recipes = llm_api_interface.request_pricing(recipes)
        ingredients = list(priced_recipes[0]["ingredients"].items())
        names = [name for name, _price in ingredients]
        ownership = identify_owned_recipe_ingredients(names, [])
        priced = [
            {"name": name, "estimated_price": price, "owned": is_owned}
            for (name, price), is_owned in zip(
                ingredients,
                ownership,
                strict=True,
            )
        ]
        costs = calculate_recipe_costs(priced, budget=100.0)
    capsys.readouterr()

    assert priced_recipes[0]["ingredients"]["broccoli"] == 2.49
    assert priced_recipes[0]["ingredients"]["chicken"] == 1.0
    assert priced_recipes[0]["total_cost"] == 6.49
    assert costs["estimated_total_cost"] == 6.49
    assert costs["additional_purchase_cost"] == 6.49
    assert {
        timing.stage for timing in measurement.stage_timings
    } == {
        "pricing_request_preparation",
        "in_memory_lookup",
        "pricing_response_processing",
        "ingredient_ownership_matching",
        "recipe_cost_calculation",
    }


def test_csv_rows_have_required_fields_and_attempt_metadata():
    measurement = PricingMeasurement("test", "local", "fixture")
    with measurement.measure("pricing_workflow_total"):
        pass
    measurement.mark_success()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=benchmark_pricing.CSV_FIELDS)
    writer.writeheader()
    writer.writerows(benchmark_pricing._measurement_rows(measurement))
    row = next(csv.DictReader(io.StringIO(output.getvalue())))

    assert set(row) == set(benchmark_pricing.CSV_FIELDS)
    assert row["run_id"] == measurement.run_id
    assert row["mode"] == "local"
    assert row["stage"] == "pricing_workflow_total"
    assert row["duration_ns"].isdigit()
    assert row["status"] == "success"
    assert row["attempt_count"] == "0"
    assert row["retry_attempts"] == "0"
    assert row["provider_request_count"] == "0"


def test_summary_calculates_distribution_statistics():
    rows = [
        {
            "run_id": f"run-{value}",
            "scenario": "actual_in_memory_dictionary",
            "mode": "local",
            "input_dataset_id": "test",
            "stage": "pricing_workflow_total",
            "status": "success",
            "duration_ns": str(value * 1_000_000_000),
        }
        for value in (1, 2, 3)
    ]

    summary = analyze_pricing_benchmark.summarize_rows(rows)[0]

    assert summary["run_count"] == 3
    assert summary["sample_count"] == 3
    assert summary["minimum_duration_s"] == 1
    assert summary["maximum_duration_s"] == 3
    assert summary["mean_duration_s"] == 2
    assert summary["median_duration_s"] == 2
    assert summary["sample_standard_deviation_s"] == 1


def test_llm_pricing_response_requires_exact_finite_estimates():
    result = pricing_estimator.validate_price_estimates(
        _VALID_PRICES,
        _INGREDIENTS,
    )

    assert result[0] == {
        "ingredient": "chicken",
        "estimated_price_usd": 4.5,
    }
    assert result[2]["estimated_price_usd"] == 2.49


@pytest.mark.parametrize(
    "output_text",
    [
        "not json",
        json.dumps({"prices": []}),
        json.dumps(
            {
                "prices": [
                    {
                        "ingredient": "chicken",
                        "estimated_price_usd": float("nan"),
                    }
                ]
            }
        ),
        json.dumps(
            {
                "prices": [
                    {"ingredient": "chicken", "estimated_price_usd": 1},
                    {"ingredient": "chicken", "estimated_price_usd": 2},
                    {"ingredient": "broccoli", "estimated_price_usd": 2},
                    {"ingredient": "olive oil", "estimated_price_usd": 3},
                    {"ingredient": "garlic", "estimated_price_usd": 1},
                ]
            }
        ),
    ],
)
def test_llm_pricing_response_rejects_malformed_or_unmatched_values(
    output_text,
):
    with pytest.raises(PricingBenchmarkError):
        pricing_estimator.validate_price_estimates(output_text, _INGREDIENTS)


def test_pricing_client_uses_server_config_and_disables_sdk_retries(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, *, api_key, timeout, max_retries):
            captured.update(
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            )

    monkeypatch.setattr(pricing_estimator, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENAI_MODEL", "configured-test-model")

    _client, model = pricing_estimator.create_pricing_client()

    assert model == "configured-test-model"
    assert captured == {
        "api_key": "test-only-key",
        "timeout": 30.0,
        "max_retries": 0,
    }


def test_provider_failure_is_sanitized_and_not_retried():
    calls = []

    class FakeResponses:
        def create(self, **_kwargs):
            calls.append(True)
            raise OpenAIError("provider detail must not be recorded")

    client = SimpleNamespace(responses=FakeResponses())
    request_input = pricing_estimator.build_pricing_request(_INGREDIENTS)
    with pytest.raises(PricingBenchmarkError) as error:
        pricing_estimator.request_price_estimates(
            client,
            "configured-model",
            request_input,
        )

    assert error.value.failure_code == "openai_OpenAIError"
    assert "provider detail" not in str(error.value)
    assert calls == [True]


def test_llm_request_uses_strict_structured_output_with_fake_provider():
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text=_VALID_PRICES)

    request_input = pricing_estimator.build_pricing_request(_INGREDIENTS)
    output = pricing_estimator.request_price_estimates(
        SimpleNamespace(responses=FakeResponses()),
        "selected-model",
        request_input,
    )

    assert output == _VALID_PRICES
    assert captured["model"] == "selected-model"
    assert captured["text"]["format"]["strict"] is True
    assert captured["text"]["format"]["schema"]["required"] == ["prices"]
    assert json.loads(captured["input"][1]["content"]) == {
        "ingredients": _INGREDIENTS,
    }


def test_llm_benchmark_records_one_attempt_and_no_retries(monkeypatch):
    monkeypatch.setattr(
        benchmark_pricing,
        "create_pricing_client",
        lambda: (object(), "selected-model"),
    )
    monkeypatch.setattr(
        benchmark_pricing,
        "request_price_estimates",
        lambda _client, _model, _ingredients: _VALID_PRICES,
    )
    measurement = PricingMeasurement(
        "experimental_llm_pricing",
        "llm",
        "test",
    )

    benchmark_pricing._run_llm_pricing(measurement)

    attempt = next(
        timing
        for timing in measurement.stage_timings
        if timing.stage == "llm_pricing_attempt"
    )
    assert measurement.model == "selected-model"
    assert measurement.attempt_count == 1
    assert measurement.retry_attempts == 0
    assert measurement.provider_request_count == 0
    assert attempt.attempt_number == 1
    assert attempt.status == "success"
    assert {
        timing.stage for timing in measurement.stage_timings
    }.issuperset(
        {
            "ingredient_ownership_matching",
            "recipe_cost_calculation",
        }
    )


def test_failed_llm_attempt_is_recorded_without_retry(monkeypatch):
    monkeypatch.setattr(
        benchmark_pricing,
        "create_pricing_client",
        lambda: (object(), "selected-model"),
    )

    def fail_request(_client, _model, _request_input):
        raise PricingBenchmarkError("controlled_timeout")

    monkeypatch.setattr(
        benchmark_pricing,
        "request_price_estimates",
        fail_request,
    )
    measurement = PricingMeasurement(
        "experimental_llm_pricing",
        "llm",
        "test",
    )

    with pytest.raises(PricingBenchmarkError):
        benchmark_pricing._run_llm_pricing(measurement)

    attempt = next(
        timing
        for timing in measurement.stage_timings
        if timing.stage == "llm_pricing_attempt"
    )
    assert measurement.attempt_count == 1
    assert measurement.retry_attempts == 0
    assert attempt.status == "failure"
    assert measurement.run_status == "failure"


def test_llm_pricing_request_counts_external_http_attempts():
    class FakeResponses:
        def create(self, **_kwargs):
            return SimpleNamespace(output_text=_VALID_PRICES)

    client = SimpleNamespace(responses=FakeResponses())
    request_input = pricing_estimator.build_pricing_request(_INGREDIENTS)
    measurement = PricingMeasurement("test", "llm", "fixture")

    with activate_measurement(measurement):
        pricing_estimator.request_price_estimates(
            client,
            "test-model",
            request_input,
        )

    assert measurement.provider_request_count == 1


def test_external_request_budget_stops_before_exceeding_cap():
    budget = ExternalRequestBudget(max_requests=1)
    measurement = PricingMeasurement("test", "html_fixture", "fixture")

    with activate_request_budget(budget), activate_measurement(measurement):
        record_external_request()
        with pytest.raises(ExternalRequestBudgetExceeded):
            record_external_request()

    assert budget.request_count == 1
    assert measurement.provider_request_count == 1


def test_html_fixture_benchmark_is_local_and_needs_no_live_opt_in():
    args = benchmark_pricing._parse_args(
        [
            "--mode",
            "html-fixture",
            "--runs",
            "30",
        ]
    )

    assert args.mode == "html-fixture"
    assert args.runs == 30
    assert args.live is False


def test_kroger_benchmark_requires_explicit_live_flag():
    with pytest.raises(SystemExit):
        benchmark_pricing._parse_args(
            [
                "--mode",
                "kroger",
                "--runs",
                "1",
                "--max-requests",
                "6",
            ]
        )


def test_kroger_benchmark_requires_and_accepts_explicit_http_cap():
    args = benchmark_pricing._parse_args(
        [
            "--mode",
            "kroger",
            "--live",
            "--runs",
            "30",
            "--max-requests",
            "180",
        ]
    )

    assert args.mode == "kroger"
    assert args.runs == 30
    assert args.max_requests == 180


def test_kroger_benchmark_rejects_http_cap_above_180():
    with pytest.raises(SystemExit):
        benchmark_pricing._parse_args(
            [
                "--mode",
                "kroger",
                "--live",
                "--runs",
                "30",
                "--max-requests",
                "181",
            ]
        )


def test_local_benchmark_does_not_create_an_openai_client(monkeypatch, capsys):
    def forbidden_client():
        pytest.fail("Local pricing must stay inside the dictionary workflow.")

    monkeypatch.setattr(
        benchmark_pricing,
        "create_pricing_client",
        forbidden_client,
    )
    measurement = PricingMeasurement(
        "actual_in_memory_dictionary",
        "local",
        "test",
    )

    benchmark_pricing._run_local_pricing(measurement)
    capsys.readouterr()

    assert measurement.run_status == "success"
    assert measurement.attempt_count == 0


def test_local_benchmark_forces_stub_mode(monkeypatch, capsys):
    from grocery_store_interface import get_grocery_pricing_mode

    monkeypatch.setenv("GROCERY_PRICING_MODE", "html_live")
    measurement = PricingMeasurement(
        "actual_in_memory_dictionary",
        "local",
        "test",
    )

    benchmark_pricing._run_local_pricing(measurement)
    capsys.readouterr()

    assert get_grocery_pricing_mode() == "html_live"
    assert measurement.provider_request_count == 0
    assert measurement.run_status == "success"


def test_html_fixture_benchmark_has_no_external_requests(monkeypatch, capsys):
    from grocery_store_interface import get_grocery_pricing_mode

    monkeypatch.setenv("GROCERY_PRICING_MODE", "html_live")
    measurement = PricingMeasurement(
        "actual_html_fixture_pricing",
        "html_fixture",
        "test",
    )

    benchmark_pricing._run_html_fixture_pricing(measurement)
    capsys.readouterr()

    assert get_grocery_pricing_mode() == "html_live"
    assert measurement.provider_request_count == 0
    assert measurement.run_status == "success"


def test_kroger_benchmark_selects_api_mode_without_live_test_requests(
    monkeypatch,
    capsys,
):
    from grocery_store_interface import get_grocery_pricing_mode

    monkeypatch.setenv("GROCERY_PRICING_MODE", "html_fixture")

    def fake_pricing(_recipes):
        assert get_grocery_pricing_mode() == "kroger"
        return [
            {
                "ingredients": {"chicken": 1.0},
            }
        ]

    monkeypatch.setattr(benchmark_pricing, "request_pricing", fake_pricing)
    measurement = PricingMeasurement(
        "actual_kroger_api_pricing",
        "kroger",
        "test",
    )

    benchmark_pricing._run_kroger_pricing(measurement)
    capsys.readouterr()

    assert get_grocery_pricing_mode() == "html_fixture"
    assert measurement.provider_request_count == 0
    assert measurement.run_status == "success"


def test_cancelled_kroger_benchmark_sends_no_requests(monkeypatch, tmp_path):
    monkeypatch.setattr(
        benchmark_pricing,
        "_confirm_live_run",
        lambda *_args: False,
    )

    def forbidden_request(*_args, **_kwargs):
        pytest.fail("A cancelled benchmark must not send HTTP.")

    monkeypatch.setattr(
        "grocery_store_interface.kroger_api._open_request",
        forbidden_request,
    )
    output = tmp_path / "cancelled-kroger.csv"

    result = benchmark_pricing.main(
        [
            "--mode",
            "kroger",
            "--live",
            "--runs",
            "1",
            "--max-requests",
            "6",
            "--output",
            str(output),
        ]
    )

    assert result == 2
    assert not output.exists()


def test_comparison_keeps_s3_simulation_values_pending():
    reference = analyze_pricing_benchmark._read_csv(
        analyze_pricing_benchmark.DEFAULT_REFERENCE
    )
    comparison = analyze_pricing_benchmark.build_comparison_rows([], reference)
    s3 = next(
        row
        for row in comparison
        if row["record_type"] == "innoslate_simulation"
        and row["scenario_id"] == "S.3"
    )
    llm_actual = next(
        row for row in comparison if row["scenario_id"] == "ACTUAL-LLM"
    )

    assert s3["mean_duration_s"] == ""
    assert s3["run_count"] == ""
    assert llm_actual["reference_mean_duration_s"] == ""
    assert "not present" in llm_actual["comparability_note"]


def test_fixture_timing_is_not_compared_as_live_s1_scraping():
    reference = analyze_pricing_benchmark._read_csv(
        analyze_pricing_benchmark.DEFAULT_REFERENCE
    )
    summaries = [
        {
            "scenario": "actual_html_fixture_pricing",
            "mode": "html_fixture",
            "input_dataset_id": "test",
            "stage": "pricing_workflow_total",
            "status": "success",
            "run_count": 30,
            "minimum_duration_s": 0.01,
            "maximum_duration_s": 0.02,
            "mean_duration_s": 0.015,
            "median_duration_s": 0.015,
            "sample_standard_deviation_s": 0.001,
        }
    ]

    fixture = next(
        row
        for row in analyze_pricing_benchmark.build_comparison_rows(
            summaries,
            reference,
        )
        if row["scenario_id"] == "ACTUAL-HTML-FIXTURE"
    )

    assert fixture["reference_scenario_id"] == ""
    assert fixture["reference_mean_duration_s"] == ""
    assert fixture["mean_delta_s"] == ""
    assert "not comparable to S.1" in fixture["comparability_note"]


def test_kroger_api_comparison_is_labeled_as_s1_source_substitution():
    reference = analyze_pricing_benchmark._read_csv(
        analyze_pricing_benchmark.DEFAULT_REFERENCE
    )
    summaries = [
        {
            "scenario": "actual_kroger_api_pricing",
            "mode": "kroger",
            "input_dataset_id": "test",
            "stage": "pricing_workflow_total",
            "status": "success",
            "run_count": 1,
            "minimum_duration_s": 1.0,
            "maximum_duration_s": 1.0,
            "mean_duration_s": 1.0,
            "median_duration_s": 1.0,
            "sample_standard_deviation_s": "",
        }
    ]

    kroger = next(
        row
        for row in analyze_pricing_benchmark.build_comparison_rows(
            summaries,
            reference,
        )
        if row["scenario_id"] == "ACTUAL-KROGER-API"
    )

    assert kroger["reference_scenario_id"] == "S.1"
    assert kroger["reference_mean_duration_s"] == 17.185
    assert "not literal HTML scraping" in kroger["comparability_note"]


def test_comparison_preserves_zero_duration_measurement():
    reference = analyze_pricing_benchmark._read_csv(
        analyze_pricing_benchmark.DEFAULT_REFERENCE
    )
    summaries = [
        {
            "scenario": "actual_in_memory_dictionary",
            "mode": "local",
            "input_dataset_id": "test",
            "stage": "pricing_workflow_total",
            "status": "success",
            "run_count": 1,
            "minimum_duration_s": 0.0,
            "maximum_duration_s": 0.0,
            "mean_duration_s": 0.0,
            "median_duration_s": 0.0,
            "sample_standard_deviation_s": "",
        }
    ]

    local = next(
        row
        for row in analyze_pricing_benchmark.build_comparison_rows(
            summaries,
            reference,
        )
        if row["scenario_id"] == "ACTUAL-LOCAL"
    )

    assert local["mean_duration_s"] == 0.0
    assert local["mean_delta_s"] == -6.86


def test_analyzer_refuses_to_overwrite_existing_analysis_outputs(
    tmp_path,
    capsys,
):
    measurement_csv = tmp_path / "measurements.csv"
    with measurement_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=benchmark_pricing.CSV_FIELDS,
        )
        writer.writeheader()

    output_dir = tmp_path / "analysis"
    output_dir.mkdir()
    existing_summary = output_dir / "stage-summary.csv"
    existing_summary.write_text("preserve this history\n", encoding="utf-8")

    result = analyze_pricing_benchmark.main(
        [
            "--input",
            str(measurement_csv),
            "--output-dir",
            str(output_dir),
        ]
    )
    capsys.readouterr()

    assert result == 2
    assert existing_summary.read_text(encoding="utf-8") == (
        "preserve this history\n"
    )
    assert not (output_dir / "scenario-comparison.csv").exists()


def test_llm_mode_without_opt_in_is_rejected_before_provider_use():
    with pytest.raises(SystemExit):
        benchmark_pricing._parse_args(
            [
                "--mode",
                "llm",
                "--runs",
                "1",
                "--max-requests",
                "1",
            ]
        )


def test_cancelled_live_benchmark_never_creates_client(monkeypatch, tmp_path):
    monkeypatch.setattr(
        benchmark_pricing,
        "_confirm_live_run",
        lambda *_args: False,
    )

    def forbidden_client():
        pytest.fail("No client may be created after confirmation is declined.")

    monkeypatch.setattr(
        benchmark_pricing,
        "create_pricing_client",
        forbidden_client,
    )
    output = tmp_path / "live.csv"

    result = benchmark_pricing.main(
        [
            "--mode",
            "llm",
            "--live",
            "--runs",
            "1",
            "--max-requests",
            "1",
            "--output",
            str(output),
        ]
    )

    assert result == 2
    assert not output.exists()
