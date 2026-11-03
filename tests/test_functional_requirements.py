import pytest
from flask import Flask

import app
import recipe_service


@pytest.fixture
def client():
    flask_app = app.create_app({"TESTING": True})
    return flask_app.test_client()


def test_application_factory_initializes_flask_app():
    flask_app = app.create_app({"TESTING": True})

    assert isinstance(flask_app, Flask)
    assert flask_app.config["TESTING"] is True


def test_homepage_returns_successful_response(client):
    response = client.get("/")

    assert response.status_code == 200


def test_homepage_contains_recipe_roulette_branding(client):
    response = client.get("/")

    assert b"Recipe Roulette" in response.data


def test_homepage_startup_does_not_run_console_workflow(monkeypatch):
    def fail_if_console_runs():
        pytest.fail("The web application must not invoke console prompts.")

    monkeypatch.setattr(app, "run_baseline_scenario", fail_if_console_runs)
    response = app.create_app({"TESTING": True}).test_client().get("/")

    assert response.status_code == 200


def test_cli_option_keeps_walking_skeleton_accessible(monkeypatch):
    calls = []
    monkeypatch.setattr(app, "run_baseline_scenario", lambda: calls.append(True))

    app.main(["--cli"])

    assert calls == [True]


def test_f24_submits_requirements_to_recipe_and_pricing_stubs(client):
    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta", "eggs"],
            "budget": 20,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 200
    assert response.get_json()["recipes"][0]["name"] == "Pasta Carbonara"


def test_recipe_endpoint_returns_contract_response_structure(client):
    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta"],
            "budget": 20.0,
            "dietary_restrictions": [],
        },
    )

    body = response.get_json()
    assert set(body) == {"recipes"}
    assert body["recipes"]
    for recipe in body["recipes"]:
        assert set(recipe) == {"name", "ingredients", "estimated_total_cost"}
        assert isinstance(recipe["name"], str)
        assert isinstance(recipe["estimated_total_cost"], (int, float))
        assert recipe["estimated_total_cost"] >= 0
        for ingredient in recipe["ingredients"]:
            assert set(ingredient) == {"name", "estimated_price"}
            assert isinstance(ingredient["name"], str)
            assert isinstance(ingredient["estimated_price"], (int, float))


def test_recipe_endpoint_is_deterministic(client):
    payload = {
        "ingredients": ["pasta"],
        "budget": 20.0,
        "dietary_restrictions": [],
    }

    first_response = client.post("/api/v1/recipes", json=payload)
    second_response = client.post("/api/v1/recipes", json=payload)

    assert first_response.get_json() == second_response.get_json()


def test_recipe_endpoint_reports_missing_required_inputs(client):
    response = client.post("/api/v1/recipes", json={})

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "invalid_request"
    assert set(body["error"]["field_errors"]) == {
        "ingredients",
        "budget",
        "dietary_restrictions",
    }


@pytest.mark.parametrize("budget", [0, -1, True, "20", float("inf"), float("nan")])
def test_recipe_endpoint_rejects_invalid_budget_values(client, budget):
    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta"],
            "budget": budget,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 400
    assert "budget" in response.get_json()["error"]["field_errors"]


@pytest.mark.parametrize(
    "ingredients",
    ["pasta", [], [""], ["   "], [3], None],
)
def test_recipe_endpoint_rejects_invalid_ingredients(client, ingredients):
    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ingredients,
            "budget": 20,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["field_errors"]


def test_recipe_endpoint_normalizes_preferences_and_passes_restrictions(
    client, monkeypatch
):
    original_send = recipe_service.send_recipe_requirements
    submitted = {}

    def capture_request(ingredients, budget, dietary_restrictions):
        submitted.update(
            ingredients=ingredients,
            budget=budget,
            dietary_restrictions=dietary_restrictions,
        )
        return original_send(ingredients, budget, dietary_restrictions)

    monkeypatch.setattr(recipe_service, "send_recipe_requirements", capture_request)
    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["  pasta  ", " eggs"],
            "budget": 20,
            "dietary_restrictions": [" vegetarian "],
        },
    )

    assert response.status_code == 200
    assert submitted == {
        "ingredients": ["pasta", "eggs"],
        "budget": 20.0,
        "dietary_restrictions": ["vegetarian"],
    }


def test_recipe_endpoint_allows_no_dietary_restrictions(client):
    response = client.post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta"],
            "budget": 20,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 200


def test_recipe_endpoint_rejects_malformed_json(client):
    response = client.post(
        "/api/v1/recipes",
        data="{",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_recipe_endpoint_returns_safe_backend_failure_response(monkeypatch):
    flask_app = app.create_app(
        {"TESTING": True, "PROPAGATE_EXCEPTIONS": False}
    )

    def fail_generation(recipe_request):
        del recipe_request
        raise RuntimeError("internal detail must not be exposed")

    monkeypatch.setattr(
        "user_interface.routes.submit_recipe_and_pricing_requests",
        fail_generation,
    )
    response = flask_app.test_client().post(
        "/api/v1/recipes",
        json={
            "ingredients": ["pasta"],
            "budget": 20,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 500
    assert response.get_json() == {
        "error": {
            "code": "backend_failure",
            "message": (
                "Recipe generation is temporarily unavailable. Please try again."
            ),
        }
    }


def test_console_walking_skeleton_remains_compatible(monkeypatch, capsys):
    input_values = iter(
        ["demo-user", "demo-password", "pasta, eggs", "20", ""]
    )

    def fake_input(prompt=""):
        print(prompt, end="")
        return next(input_values)

    monkeypatch.setattr("builtins.input", fake_input)

    app.run_baseline_scenario()

    output = capsys.readouterr().out
    assert "Recipe: Pasta Carbonara" in output
    assert "Recipe: Vegetable Stir-Fry" in output
    assert "Total Cost: $11.47" in output
    assert "Total Cost: $8.46" in output
