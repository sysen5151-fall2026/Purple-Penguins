"""Recipe request workflow for F.2.4.1-F.2.4.3.

The service uses deterministic local interfaces; it makes no external requests.
"""

import math
from typing import TypedDict

from llm_api_interface import request_pricing, send_recipe_requirements


class RecipeRequest(TypedDict):
    ingredients: list[str]
    budget: float
    dietary_restrictions: list[str]


class PricedIngredient(TypedDict):
    name: str
    estimated_price: float


class RecipeResult(TypedDict):
    name: str
    ingredients: list[PricedIngredient]
    estimated_total_cost: float


class RecipeGenerationResponse(TypedDict):
    recipes: list[RecipeResult]


class RecipeRequestValidationError(ValueError):
    """Raised when a request does not match the published API contract."""

    def __init__(self, field_errors: dict[str, str]):
        self.field_errors = field_errors
        super().__init__("One or more request fields are invalid.")


def prepare_recipe_request(
    ingredients: list[str],
    budget: float,
    dietary_restrictions: list[str],
) -> RecipeRequest:
    """F.2.4.1 / C.2.4.1: normalize validated recipe-request values."""
    return {
        "ingredients": [ingredient.strip() for ingredient in ingredients],
        "budget": float(budget),
        "dietary_restrictions": [
            restriction.strip() for restriction in dietary_restrictions
        ],
    }


def format_and_validate_api_request(payload: object) -> RecipeRequest:
    """F.2.4.2 / C.2.4.2: validate and format the OpenAPI request shape."""
    if not isinstance(payload, dict):
        raise RecipeRequestValidationError(
            {"body": "Must be a JSON object."}
        )

    field_errors: dict[str, str] = {}
    required_fields = {"ingredients", "budget", "dietary_restrictions"}
    allowed_fields = required_fields

    for field in sorted(required_fields - payload.keys()):
        field_errors[field] = "This field is required."

    unexpected_fields = sorted(payload.keys() - allowed_fields)
    if unexpected_fields:
        field_errors["additionalProperties"] = (
            f"Unexpected field(s): {', '.join(unexpected_fields)}."
        )

    ingredients_value = payload.get("ingredients")
    ingredients: list[str] = []
    if "ingredients" in payload:
        if not isinstance(ingredients_value, list):
            field_errors["ingredients"] = "Must be an array of strings."
        elif not ingredients_value:
            field_errors["ingredients"] = "Must contain at least one ingredient."
        else:
            for index, value in enumerate(ingredients_value):
                if not isinstance(value, str) or not value.strip():
                    field_errors[f"ingredients.{index}"] = (
                        "Must be a non-empty string."
                    )
                else:
                    ingredients.append(value.strip())

    budget_value = payload.get("budget")
    budget: float | None = None
    if "budget" in payload:
        if isinstance(budget_value, bool) or not isinstance(
            budget_value, (int, float)
        ):
            field_errors["budget"] = "Must be a positive number."
        else:
            try:
                normalized_budget = float(budget_value)
            except OverflowError:
                field_errors["budget"] = "Must be a finite positive number."
            else:
                if not math.isfinite(normalized_budget) or normalized_budget <= 0:
                    field_errors["budget"] = "Must be a finite positive number."
                else:
                    budget = normalized_budget

    restrictions_value = payload.get("dietary_restrictions")
    dietary_restrictions: list[str] = []
    if "dietary_restrictions" in payload:
        if not isinstance(restrictions_value, list):
            field_errors["dietary_restrictions"] = "Must be an array of strings."
        else:
            for index, value in enumerate(restrictions_value):
                if not isinstance(value, str) or not value.strip():
                    field_errors[f"dietary_restrictions.{index}"] = (
                        "Must be a non-empty string."
                    )
                else:
                    dietary_restrictions.append(value.strip())

    if field_errors:
        raise RecipeRequestValidationError(field_errors)

    return prepare_recipe_request(
        ingredients=ingredients,
        budget=budget,
        dietary_restrictions=dietary_restrictions,
    )


def submit_recipe_and_pricing_requests(
    recipe_request: RecipeRequest,
) -> RecipeGenerationResponse:
    """F.2.4.3 / C.2.4.3: call the recipe and pricing interface boundaries."""
    recipes = send_recipe_requirements(
        ingredients=recipe_request["ingredients"],
        budget=recipe_request["budget"],
        dietary_restrictions=recipe_request["dietary_restrictions"],
    )
    recipes_with_pricing = request_pricing(recipes)

    results: list[RecipeResult] = []
    for recipe in recipes_with_pricing:
        priced_ingredients: list[PricedIngredient] = [
            {
                "name": ingredient,
                "estimated_price": round(float(price), 2),
            }
            for ingredient, price in recipe["ingredients"].items()
        ]
        results.append(
            {
                "name": recipe["name"],
                "ingredients": priced_ingredients,
                "estimated_total_cost": round(float(recipe["total_cost"]), 2),
            }
        )

    return {"recipes": results}
