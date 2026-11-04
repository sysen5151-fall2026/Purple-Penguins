"""Recipe request workflow and deterministic ingredient-aware pricing.

The service uses deterministic local interfaces; it makes no external requests.
The verified Innoslate mapping covers F.2.4.1-F.2.4.4. Additional-cost
calculation remains an unallocated service-level responsibility.
"""

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import TypedDict

from llm_api_interface import request_pricing, send_recipe_requirements


class RecipeRequest(TypedDict):
    ingredients: list[str]
    budget: float
    dietary_restrictions: list[str]


class RecipeRequestWithOwnership(RecipeRequest):
    owned_ingredient_names: list[str]


class PricedIngredient(TypedDict):
    name: str
    estimated_price: float
    owned: bool


class RecipeResult(TypedDict):
    name: str
    ingredients: list[PricedIngredient]
    estimated_total_cost: float
    additional_purchase_cost: float
    within_budget: bool


class RecipeCostSummary(TypedDict):
    estimated_total_cost: float
    additional_purchase_cost: float
    within_budget: bool


class RecipeGenerationResponse(TypedDict):
    recipes: list[RecipeResult]


class RecipeRequestValidationError(ValueError):
    """Raised when a request does not match the published API contract."""

    def __init__(self, field_errors: dict[str, str]):
        self.field_errors = field_errors
        super().__init__("One or more request fields are invalid.")


def _normalize_ingredient_name(name: str) -> str:
    return name.strip().casefold()


def _price_to_cents(price: float) -> int:
    try:
        amount = Decimal(str(price))
    except InvalidOperation as error:
        raise ValueError("Ingredient prices must be finite and non-negative.") from error

    if not amount.is_finite() or amount < 0:
        raise ValueError("Ingredient prices must be finite and non-negative.")

    return int(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)


def _dollars_from_cents(cents: int) -> float:
    return float(Decimal(cents) / 100)


def identify_owned_recipe_ingredients(
    recipe_ingredients: list[str],
    user_owned_ingredients: list[str],
) -> list[bool]:
    """Return exact, case-insensitive ownership matches in recipe order."""
    owned_names = {
        _normalize_ingredient_name(ingredient)
        for ingredient in user_owned_ingredients
    }
    return [
        _normalize_ingredient_name(ingredient) in owned_names
        for ingredient in recipe_ingredients
    ]


def calculate_recipe_costs(
    priced_ingredients: list[PricedIngredient],
    budget: float,
) -> RecipeCostSummary:
    """Calculate full and additional costs using whole-cent arithmetic."""
    full_cost_cents = 0
    additional_cost_cents = 0
    for ingredient in priced_ingredients:
        price_cents = _price_to_cents(ingredient["estimated_price"])
        full_cost_cents += price_cents
        if not ingredient["owned"]:
            additional_cost_cents += price_cents

    additional_cost = Decimal(additional_cost_cents) / 100
    return {
        "estimated_total_cost": _dollars_from_cents(full_cost_cents),
        "additional_purchase_cost": _dollars_from_cents(additional_cost_cents),
        "within_budget": additional_cost <= Decimal(str(budget)),
    }


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


def specify_already_owned_recipe_ingredients(
    recipe_request: RecipeRequest,
) -> RecipeRequestWithOwnership:
    """F.2.4.3 / C.2.4.3: normalize and deduplicate owned ingredient names."""
    owned_ingredient_names = list(
        dict.fromkeys(
            _normalize_ingredient_name(ingredient)
            for ingredient in recipe_request["ingredients"]
        )
    )
    return {
        **recipe_request,
        "owned_ingredient_names": owned_ingredient_names,
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
    recipe_request: RecipeRequestWithOwnership,
) -> RecipeGenerationResponse:
    """F.2.4.4 / C.2.4.4: call the recipe and pricing interface boundaries."""
    recipes = send_recipe_requirements(
        ingredients=recipe_request["ingredients"],
        budget=recipe_request["budget"],
        dietary_restrictions=recipe_request["dietary_restrictions"],
    )
    recipes_with_pricing = request_pricing(recipes)

    results: list[RecipeResult] = []
    for recipe in recipes_with_pricing:
        priced_ingredients: list[PricedIngredient] = []
        ingredient_items = list(recipe["ingredients"].items())
        ownership = identify_owned_recipe_ingredients(
            [ingredient for ingredient, _price in ingredient_items],
            recipe_request["owned_ingredient_names"],
        )
        for (ingredient, price), is_owned in zip(
            ingredient_items, ownership, strict=True
        ):
            price_cents = _price_to_cents(price)
            priced_ingredients.append(
                {
                    "name": ingredient,
                    "estimated_price": _dollars_from_cents(price_cents),
                    "owned": is_owned,
                }
            )

        cost_summary = calculate_recipe_costs(
            priced_ingredients,
            recipe_request["budget"],
        )
        results.append(
            {
                "name": recipe["name"],
                "ingredients": priced_ingredients,
                **cost_summary,
            }
        )

    return {"recipes": results}
