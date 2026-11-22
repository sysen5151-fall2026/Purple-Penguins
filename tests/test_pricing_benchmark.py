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
    PricingMeasurement,
    activate_measurement,
    measure_stage,
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
            "ingredients": _INGREDIENTS,
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
        "pricing_request_processing",
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


def test_summary_calculates_distribution_statistics():
    rows = [
        {
            "scenario": "actual_in_memory_dictionary",
            "mode": "local",
            "stage": "pricing_workflow_total",
            "status": "success",
            "duration_ns": str(value * 1_000_000_000),
        }
        for value in (1, 2, 3)
    ]

    summary = analyze_pricing_benchmark.summarize_rows(rows)[0]

    assert summary["run_count"] == 3
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


def test_llm_price_estimate_request_includes_store_and_zip_context():
    request_input = pricing_estimator.build_pricing_request(
        ["pasta"],
        store="Walmart",
        zip_code="00501",
    )

    assert json.loads(request_input[1]["content"]) == {
        "ingredients": ["pasta"],
        "store": "Walmart",
        "zip_code": "00501",
    }
    assert "do not have live access" in request_input[0]["content"].casefold()
    assert (
        "do not claim that any estimate is current or verified"
        in request_input[0]["content"].casefold()
    )


def test_estimate_store_prices_uses_mocked_openai_with_location_context(
    monkeypatch,
):
    captured = {}
    output = json.dumps(
        {
            "prices": [
                {"ingredient": "pasta", "estimated_price_usd": 3.25},
            ]
        }
    )

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text=output)

    class FakeClient:
        def __init__(self, *, api_key, timeout, max_retries):
            assert api_key == "test-only-key"
            assert timeout == 30.0
            assert max_retries == 0
            self.responses = FakeResponses()

    monkeypatch.setattr(pricing_estimator, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")

    prices = pricing_estimator.estimate_store_prices(
        ["pasta"],
        store="Wegmans",
        zip_code="00501",
    )

    assert prices == {"pasta": 3.25}
    assert json.loads(captured["input"][1]["content"]) == {
        "ingredients": ["pasta"],
        "store": "Wegmans",
        "zip_code": "00501",
    }


def test_store_estimator_maps_missing_credentials_to_safe_service_error(
    monkeypatch,
):
    from llm_api_interface.errors import RecipeGenerationServiceError

    def fail_client():
        raise PricingBenchmarkError("missing_api_key")

    monkeypatch.setattr(pricing_estimator, "create_pricing_client", fail_client)

    with pytest.raises(RecipeGenerationServiceError) as error:
        pricing_estimator.estimate_store_prices(
            ["pasta"],
            store="Walmart",
            zip_code="14850",
        )

    assert error.value.status_code == 503
    assert "temporarily unavailable" in error.value.public_message
    assert "OPENAI_API_KEY" not in error.value.public_message


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


def test_llm_pricing_response_rejects_unrepresentable_price():
    output = json.dumps(
        {
            "prices": [
                {"ingredient": "pasta", "estimated_price_usd": 10**400},
            ]
        }
    )

    with pytest.raises(PricingBenchmarkError) as error:
        pricing_estimator.validate_price_estimates(output, ["pasta"])

    assert error.value.failure_code == "invalid_estimated_price"


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


def test_comparison_preserves_zero_duration_measurement():
    reference = analyze_pricing_benchmark._read_csv(
        analyze_pricing_benchmark.DEFAULT_REFERENCE
    )
    summaries = [
        {
            "scenario": "actual_in_memory_dictionary",
            "mode": "local",
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
        lambda _run_count: False,
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
