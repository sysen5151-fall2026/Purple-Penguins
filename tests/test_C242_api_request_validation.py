"""C.2.4.2 / F.2.4.2 — API Request Validation Component.

Baseline: contracts/api-v1.yaml and current recipe_service.py implementation.
These are unit tests for the component, not tests of Flask's JSON parsing.
The detailed rules should be formally traced to approved Innoslate requirements.

Run from the repository root:
    python -m pytest -q tests/test_C242_api_request_validation.py
"""

import copy
import math

import pytest

from recipe_service import (
    RecipeRequestValidationError,
    format_and_validate_api_request,
)


@pytest.fixture
def valid_request():
    return {
        "ingredients": [" pasta ", " eggs"],
        "budget": 20,
        "dietary_restrictions": [" vegetarian "],
    }


def assert_invalid(payload, *expected_fields):
    with pytest.raises(RecipeRequestValidationError) as exc_info:
        format_and_validate_api_request(payload)
    errors = exc_info.value.field_errors
    assert isinstance(errors, dict)
    assert set(expected_fields).issubset(errors.keys())
    assert all(isinstance(message, str) and message for message in errors.values())
    return errors


def test_C242_01_valid_request_is_normalized(valid_request):
    result = format_and_validate_api_request(valid_request)
    assert result == {
        "ingredients": ["pasta", "eggs"],
        "budget": 20.0,
        "dietary_restrictions": ["vegetarian"],
    }


def test_C242_02_empty_dietary_restrictions_are_allowed(valid_request):
    valid_request["dietary_restrictions"] = []
    assert format_and_validate_api_request(valid_request)["dietary_restrictions"] == []


@pytest.mark.parametrize("payload", [None, [], "not an object", 7, True])
def test_C242_03_non_object_body_is_rejected(payload):
    assert_invalid(payload, "body")


@pytest.mark.parametrize("missing", ["ingredients", "budget", "dietary_restrictions"])
def test_C242_04_each_required_field_is_enforced(valid_request, missing):
    del valid_request[missing]
    assert_invalid(valid_request, missing)


def test_C242_05_multiple_missing_fields_reported_together():
    errors = assert_invalid({}, "ingredients", "budget", "dietary_restrictions")
    assert len(errors) == 3


def test_C242_06_unexpected_top_level_field_rejected(valid_request):
    valid_request["servings"] = 2
    errors = assert_invalid(valid_request, "additionalProperties")
    assert "servings" in errors["additionalProperties"]


@pytest.mark.parametrize("ingredients", [None, "pasta", [], {}, 5])
def test_C242_07_ingredients_must_be_nonempty_array(valid_request, ingredients):
    valid_request["ingredients"] = ingredients
    assert_invalid(valid_request, "ingredients")


@pytest.mark.parametrize("bad_item", ["", " \t ", None, 1, False, []])
def test_C242_08_ingredient_entries_must_be_nonblank_strings(valid_request, bad_item):
    valid_request["ingredients"] = ["pasta", bad_item]
    assert_invalid(valid_request, "ingredients.1")


@pytest.mark.parametrize(
    "budget",
    [0, -0.01, -100, True, False, "20", None, [], float("nan"), float("inf"), -float("inf")],
)
def test_C242_09_budget_must_be_positive_finite_number(valid_request, budget):
    valid_request["budget"] = budget
    assert_invalid(valid_request, "budget")


def test_C242_10_positive_decimal_budget_is_accepted(valid_request):
    valid_request["budget"] = 0.01
    result = format_and_validate_api_request(valid_request)
    assert math.isclose(result["budget"], 0.01)


@pytest.mark.parametrize("restrictions", [None, "vegetarian", {}, 2])
def test_C242_11_restrictions_must_be_array(valid_request, restrictions):
    valid_request["dietary_restrictions"] = restrictions
    assert_invalid(valid_request, "dietary_restrictions")


@pytest.mark.parametrize("bad_item", ["", "  ", None, 8, False, {}])
def test_C242_12_restrictions_must_contain_nonblank_strings(valid_request, bad_item):
    valid_request["dietary_restrictions"] = ["vegetarian", bad_item]
    assert_invalid(valid_request, "dietary_restrictions.1")


def test_C242_13_multiple_invalid_fields_are_aggregated(valid_request):
    valid_request.update(
        ingredients=["", 3],
        budget=0,
        dietary_restrictions=["   "],
    )
    assert_invalid(
        valid_request,
        "ingredients.0", "ingredients.1", "budget", "dietary_restrictions.0",
    )


def test_C242_14_input_payload_is_not_mutated(valid_request):
    before = copy.deepcopy(valid_request)
    result = format_and_validate_api_request(valid_request)
    assert valid_request == before
    assert result is not valid_request
    assert result["ingredients"] is not valid_request["ingredients"]


def test_C242_15_invalid_request_never_reaches_preparation(valid_request, monkeypatch):
    import recipe_service

    def forbidden_prepare(**_kwargs):
        pytest.fail("Invalid request was passed to prepare_recipe_request")

    monkeypatch.setattr(recipe_service, "prepare_recipe_request", forbidden_prepare)
    valid_request["budget"] = -1
    assert_invalid(valid_request, "budget")
