import json
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError

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


def _install_fake_openai(monkeypatch, outcomes):
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
            assert api_key == "test-api-key"
            assert timeout == 30.0
            assert max_retries == 0
            self.responses = FakeResponses()

    monkeypatch.setattr(openai_adapter, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
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


def test_openai_missing_credentials_raise_safe_service_error(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RecipeGenerationServiceError) as error:
        llm_api_interface.send_recipe_requirements(["pasta"], 20.0, [])

    assert error.value.status_code == 503
    assert "OPENAI_API_KEY" not in error.value.public_message


def test_openai_retries_transient_connection_failure(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")

    class TransientConnectionFailure(Exception):
        pass

    monkeypatch.setattr(
        openai_adapter,
        "APIConnectionError",
        TransientConnectionFailure,
    )
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [TransientConnectionFailure("offline"), _RECIPE_RESPONSE],
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

    class TransientConnectionFailure(Exception):
        pass

    monkeypatch.setattr(
        openai_adapter,
        "APIConnectionError",
        TransientConnectionFailure,
    )
    delays = []
    monkeypatch.setattr(openai_adapter.time, "sleep", delays.append)
    calls = _install_fake_openai(
        monkeypatch,
        [TransientConnectionFailure("offline") for _ in range(10)],
    )

    with pytest.raises(RecipeGenerationServiceError) as error:
        llm_api_interface.send_recipe_requirements(["pasta"], 20.0, [])

    assert error.value.status_code == 503
    assert len(calls) == openai_adapter.MAX_TOTAL_ATTEMPTS == 10
    assert len(delays) == 9


def test_openai_does_not_retry_malformed_or_price_inventing_output(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "openai")
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

    assert b"sent from the server to OpenAI" in page
    assert b"Do not submit sensitive information" in page
    assert b"do-not-render-this-key" not in page
