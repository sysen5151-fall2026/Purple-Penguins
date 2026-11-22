import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError, OpenAI as SDKOpenAI

import app
import llm_api_interface
from llm_api_interface import openai_adapter
from llm_api_interface.errors import RecipeGenerationServiceError


_RECIPE_RESPONSE = json.dumps(
    {
        "recipes": [
            {
                "name": "Pasta Carbonara",
                "ingredients": ["pasta", "eggs", "bacon"],
            }
        ]
    }
)


class _TransientConnectionFailure(Exception):
    pass


class _ProviderStatusFailure(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code


def _install_fake_openai(monkeypatch, outcomes, *, api_key="test-api-key"):
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            outcome = outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return SimpleNamespace(output_text=outcome)

    class FakeClient:
        def __init__(self, *, api_key, timeout, max_retries):
            assert api_key == expected_api_key
            assert timeout == 30.0
            assert max_retries == 0
            self.responses = FakeResponses()

    monkeypatch.setattr(openai_adapter, "OpenAI", FakeClient)
    expected_api_key = api_key
    monkeypatch.setenv("OPENAI_API_KEY", api_key)
    return calls


def test_stub_mode_is_default_and_does_not_require_credentials(monkeypatch):
    monkeypatch.delenv("RECIPE_GENERATION_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    recipes = llm_api_interface.send_recipe_requirements(
        ["pasta"], 20.0, []
    )

    assert recipes[0]["name"] == "Pasta Carbonara"
    assert "estimated_price" not in recipes[0]


def test_openai_request_uses_structured_output_and_user_preferences(
    monkeypatch,
):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    calls = _install_fake_openai(monkeypatch, [_RECIPE_RESPONSE])

    recipes = llm_api_interface.send_recipe_requirements(
        [" spinach ", "eggs"], 25.5, ["vegetarian"]
    )

    assert recipes == [
        {
            "name": "Pasta Carbonara",
            "ingredients": ["pasta", "eggs", "bacon"],
        }
    ]
    request = calls[0]
    assert request["model"] == openai_adapter.DEFAULT_MODEL
    assert json.loads(request["input"][1]["content"]) == {
        "available_ingredients": [" spinach ", "eggs"],
        "budget_usd": 25.5,
        "dietary_restrictions": ["vegetarian"],
    }
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True
    assert request["max_output_tokens"] == openai_adapter.MAX_OUTPUT_TOKENS
    assert set(recipes[0]) == {"name", "ingredients"}


def test_openai_success_on_first_attempt_uses_one_request(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(monkeypatch, [_RECIPE_RESPONSE])

    recipes = llm_api_interface.send_recipe_requirements(
        ["pasta"], 20.0, []
    )

    assert recipes[0]["name"] == "Pasta Carbonara"
    assert len(calls) == 1
    assert delays == []


def test_openai_missing_credentials_raise_safe_service_error(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RecipeGenerationServiceError) as error:
        llm_api_interface.send_recipe_requirements(["pasta"], 20.0, [])

    assert error.value.status_code == 503
    assert "OPENAI_API_KEY" not in error.value.public_message


def test_openai_retries_transient_connection_failure(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.setattr(
        openai_adapter,
        "APIConnectionError",
        _TransientConnectionFailure,
    )
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [_TransientConnectionFailure("offline"), _RECIPE_RESPONSE],
    )

    recipes = llm_api_interface.send_recipe_requirements(
        ["pasta"], 20.0, []
    )

    assert recipes[0]["name"] == "Pasta Carbonara"
    assert len(calls) == 2
    assert delays == [1]


def test_openai_retries_timeout_exception(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [
            APITimeoutError(
                request=httpx.Request(
                    "POST", "https://api.openai.com/v1/responses"
                )
            ),
            _RECIPE_RESPONSE,
        ],
    )

    recipes = llm_api_interface.send_recipe_requirements(
        ["pasta"], 20.0, []
    )

    assert recipes[0]["name"] == "Pasta Carbonara"
    assert len(calls) == 2
    assert delays == [1]


def test_openai_retries_at_most_ten_total_attempts(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.setattr(
        openai_adapter,
        "APIConnectionError",
        _TransientConnectionFailure,
    )
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [_TransientConnectionFailure("offline") for _ in range(10)],
    )

    with pytest.raises(RecipeGenerationServiceError) as error:
        llm_api_interface.send_recipe_requirements(["pasta"], 20.0, [])

    assert error.value.status_code == 503
    assert len(calls) == openai_adapter.MAX_TOTAL_ATTEMPTS == 10
    assert len(calls) != 11
    assert len(delays) == 9
    assert delays == [1, 2, 4, 8, 8, 8, 8, 8, 8]


def test_openai_succeeds_on_tenth_attempt_then_stops(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.setattr(
        openai_adapter,
        "APIConnectionError",
        _TransientConnectionFailure,
    )
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [_TransientConnectionFailure("offline") for _ in range(9)]
        + [_RECIPE_RESPONSE],
    )

    recipes = llm_api_interface.send_recipe_requirements(
        ["pasta"], 20.0, []
    )

    assert recipes[0]["name"] == "Pasta Carbonara"
    assert len(calls) == openai_adapter.MAX_TOTAL_ATTEMPTS == 10
    assert len(calls) != 11
    assert len(delays) == 9


def test_openai_sdk_mocked_transport_observes_only_ten_total_requests(
    monkeypatch,
):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            503,
            json={
                "error": {
                    "message": "temporary outage",
                    "type": "server_error",
                }
            },
            request=request,
        )

    sdk_http_client = httpx.Client(
        transport=httpx.MockTransport(respond)
    )
    configured_retry_limits = []

    def create_sdk_client(*, api_key, timeout, max_retries):
        configured_retry_limits.append(max_retries)
        return SDKOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            http_client=sdk_http_client,
        )

    monkeypatch.setattr(openai_adapter, "OpenAI", create_sdk_client)

    try:
        with pytest.raises(RecipeGenerationServiceError) as error:
            llm_api_interface.send_recipe_requirements(
                ["pasta"], 20.0, []
            )
    finally:
        sdk_http_client.close()

    assert error.value.status_code == 503
    assert configured_retry_limits == [0]
    assert len(requests) == openai_adapter.MAX_TOTAL_ATTEMPTS == 10
    assert all(request.url.path == "/v1/responses" for request in requests)
    assert len(delays) == 9


def test_live_api_logs_safe_final_failure_after_ten_attempts(
    monkeypatch, caplog
):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    api_key = "credential-must-not-be-logged"
    monkeypatch.setattr(
        openai_adapter,
        "APIConnectionError",
        _TransientConnectionFailure,
    )
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [
            _TransientConnectionFailure(
                "provider detail must not be logged"
            )
            for _ in range(10)
        ],
        api_key=api_key,
    )
    client = app.create_app({"TESTING": True}).test_client()

    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/v1/recipes",
            json={
                "ingredients": ["pasta"],
                "budget": 20,
                "dietary_restrictions": [],
            },
        )

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "backend_failure"
    assert len(calls) == openai_adapter.MAX_TOTAL_ATTEMPTS == 10
    assert len(delays) == 9
    failure_records = [
        record for record in caplog.records
        if "Recipe-generation provider failure:" in record.getMessage()
    ]
    assert len(failure_records) == 1
    assert "after 10 total attempt(s)" in failure_records[0].getMessage()
    assert api_key not in caplog.text
    assert "provider detail must not be logged" not in caplog.text
    assert api_key not in response.get_data(as_text=True)
    assert "provider detail must not be logged" not in response.get_data(
        as_text=True
    )


@pytest.mark.parametrize(
    ("status_code", "expected_status"),
    [(400, 502), (401, 503), (403, 503)],
)
def test_openai_does_not_retry_non_retryable_statuses(
    monkeypatch, status_code, expected_status
):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.setattr(
        openai_adapter,
        "APIStatusError",
        _ProviderStatusFailure,
    )
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [_ProviderStatusFailure(status_code, "sensitive provider detail")],
    )

    with pytest.raises(RecipeGenerationServiceError) as error:
        llm_api_interface.send_recipe_requirements(["pasta"], 20.0, [])

    assert error.value.status_code == expected_status
    assert len(calls) == 1
    assert delays == []
    assert "sensitive provider detail" not in error.value.public_message


def test_openai_does_not_retry_malformed_or_price_inventing_output(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [
            json.dumps(
                {
                    "recipes": [
                        {
                            "name": "Dish",
                            "ingredients": ["rice"],
                            "estimated_price": 1.0,
                        }
                    ]
                }
            )
        ],
    )

    with pytest.raises(RecipeGenerationServiceError) as error:
        llm_api_interface.send_recipe_requirements(["rice"], 20.0, [])

    assert error.value.status_code == 502
    assert len(calls) == 1
    assert delays == []


def test_live_api_keeps_phase5_pricing_and_ownership_calculation(
    monkeypatch,
):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    _install_fake_openai(monkeypatch, [_RECIPE_RESPONSE])
    client = app.create_app({"TESTING": True}).test_client()

    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta", "eggs"],
            "budget": 5.99,
            "dietary_restrictions": [],
        },
    )

    recipe = response.get_json()["recipes"][0]
    assert response.status_code == 200
    assert recipe["name"] == "Pasta Carbonara"
    assert recipe["estimated_total_cost"] == 11.47
    assert recipe["additional_purchase_cost"] == 5.99
    assert recipe["within_budget"] is True
    assert next(
        ingredient for ingredient in recipe["ingredients"]
        if ingredient["name"] == "eggs"
    )["owned"] is True


def test_live_api_missing_credentials_returns_safe_503(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = app.create_app({"TESTING": True}).test_client()

    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta"],
            "budget": 20,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "backend_failure"
    assert "OPENAI_API_KEY" not in response.get_data(as_text=True)


def test_live_api_malformed_provider_data_returns_safe_502(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    calls = _install_fake_openai(monkeypatch, ["not valid JSON"])
    client = app.create_app({"TESTING": True}).test_client()

    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta"],
            "budget": 20,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "backend_failure"
    assert "not valid JSON" not in response.get_data(as_text=True)
    assert len(calls) == 1


def test_live_mode_discloses_external_data_use_without_exposing_credentials(
    monkeypatch,
):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-render-this-key")
    client = app.create_app({"TESTING": True}).test_client()

    page = client.get("/").data

    assert b"sent to OpenAI for recipe generation" in page
    assert b"selected store and ZIP code are sent" in page
    assert b"Do not submit other sensitive" in b" ".join(page.split())
    assert b"do-not-render-this-key" not in page
