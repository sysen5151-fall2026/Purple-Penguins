"""Recipe request workflow and deterministic ingredient-aware pricing.

The service uses deterministic local interfaces; it makes no external requests.
The verified Innoslate mapping covers F.2.4.1-F.2.4.4. Additional-cost
calculation remains an unallocated service-level responsibility.
"""

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal, TypedDict

from grocery_store_interface.models import GroceryPriceQuote, IngredientRequirement
from grocery_store_interface.units import whole_packages_required
from llm_api_interface import (
    request_pricing,
    request_pricing_with_quotes,
    send_recipe_requirements,
)
from pricing_timing import measure_stage


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


class PackagePurchaseInfo(TypedDict):
    status: Literal["available", "not_required", "unavailable"]
    source: str
    selected_product: str | None
    product_id: str | None
    package_price: float | None
    package_quantity: float | None
    package_unit: str | None
    currency: str | None
    packages_required: int | None
    purchase_cost: float | None


class PricedIngredientV2(PricedIngredient):
    package_purchase: PackagePurchaseInfo


class RecipeResultV2(TypedDict):
    name: str
    ingredients: list[PricedIngredientV2]
    estimated_total_cost: float
    additional_purchase_cost: float
    within_budget: bool
    additional_package_purchase_cost: float | None
    within_package_budget: bool | None
    package_purchase_status: Literal["available", "unavailable"]


class RecipeGenerationResponseV2(TypedDict):
    recipes: list[RecipeResultV2]


class RecipeRequestValidationError(ValueError):
    """Raised when a request does not match the published API contract."""

    def __init__(self, field_errors: dict[str, str]):
        self.field_errors = field_errors
        super().__init__("One or more request fields are invalid.")


_STANDARD_DRY_PASTA_SHAPES = {
    "angel hair",
    "farfalle",
    "fettuccine",
    "fusilli",
    "linguine",
    "macaroni",
    "penne",
    "rigatoni",
    "rotini",
    "spaghetti",
    "ziti",
}


def _normalize_ingredient_name(name: str) -> str:
    return name.strip().casefold()


def _dry_pasta_ownership_key(name: str) -> tuple[str, str | None] | None:
    tokens = name.casefold().split()
    if tokens == ["pasta"] or tokens == ["dry", "pasta"]:
        return "pasta", None
    if " ".join(tokens) in _STANDARD_DRY_PASTA_SHAPES:
        return "pasta", " ".join(tokens)
    if not tokens or tokens[0] != "dry":
        return None

    shape_tokens = tokens[1:]
    if shape_tokens and shape_tokens[-1] == "pasta":
        shape_tokens = shape_tokens[:-1]
    shape = " ".join(shape_tokens)
    if shape in _STANDARD_DRY_PASTA_SHAPES:
        return "pasta", shape
    return None


def _ownership_names_match(
    owned_name: str,
    recipe_ingredient: str,
) -> bool:
    normalized_owned = _normalize_ingredient_name(owned_name)
    normalized_recipe = _normalize_ingredient_name(recipe_ingredient)
    if normalized_owned == normalized_recipe:
        return True

    owned_pasta = _dry_pasta_ownership_key(normalized_owned)
    recipe_pasta = _dry_pasta_ownership_key(normalized_recipe)
    if owned_pasta is None or recipe_pasta is None:
        return False
    return (
        owned_pasta[1] is None
        or recipe_pasta[1] is None
        or owned_pasta[1] == recipe_pasta[1]
    )


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
    """Match exact names and a narrow, controlled dry-pasta compatibility."""
    with measure_stage("ingredient_ownership_matching"):
        return [
            any(
                _ownership_names_match(owned_name, ingredient)
                for owned_name in user_owned_ingredients
            )
            for ingredient in recipe_ingredients
        ]


def calculate_recipe_costs(
    priced_ingredients: list[PricedIngredient],
    budget: float,
) -> RecipeCostSummary:
    """Calculate full and additional costs using whole-cent arithmetic."""
    with measure_stage("recipe_cost_calculation"):
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
            "additional_purchase_cost": _dollars_from_cents(
                additional_cost_cents
            ),
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


def submit_recipe_and_pricing_requests_v2(
    recipe_request: RecipeRequestWithOwnership,
) -> RecipeGenerationResponseV2:
    """Return v1 use-cost fields plus separate full-package purchase estimates."""
    recipes = send_recipe_requirements(
        ingredients=recipe_request["ingredients"],
        budget=recipe_request["budget"],
        dietary_restrictions=recipe_request["dietary_restrictions"],
    )
    recipes_with_quotes = request_pricing_with_quotes(recipes)

    results: list[RecipeResultV2] = []
    for generated_recipe, recipe_with_quotes in zip(
        recipes,
        recipes_with_quotes,
        strict=True,
    ):
        ingredient_items = list(
            recipe_with_quotes["ingredients"].items()
        )
        ownership = identify_owned_recipe_ingredients(
            [name for name, _price in ingredient_items],
            recipe_request["owned_ingredient_names"],
        )
        priced_ingredients: list[PricedIngredientV2] = []
        for (name, price), is_owned in zip(
            ingredient_items,
            ownership,
            strict=True,
        ):
            quote = recipe_with_quotes["quotes"][name]
            requirement = next(
                item
                for item in generated_recipe["ingredients"]
                if item["name"] == name
            )
            priced_ingredients.append(
                {
                    "name": name,
                    "estimated_price": _dollars_from_cents(
                        _price_to_cents(price)
                    ),
                    "owned": is_owned,
                    "package_purchase": _package_purchase_info(
                        quote,
                        requirement,
                        is_owned,
                    ),
                }
            )

        cost_summary = calculate_recipe_costs(
            [
                {
                    "name": ingredient["name"],
                    "estimated_price": ingredient["estimated_price"],
                    "owned": ingredient["owned"],
                }
                for ingredient in priced_ingredients
            ],
            recipe_request["budget"],
        )
        package_cost_available = all(
            ingredient["package_purchase"]["status"] != "unavailable"
            for ingredient in priced_ingredients
            if not ingredient["owned"]
        )
        if package_cost_available:
            package_cost_cents = sum(
                _price_to_cents(
                    ingredient["package_purchase"]["purchase_cost"]
                )
                for ingredient in priced_ingredients
                if not ingredient["owned"]
            )
            package_cost = _dollars_from_cents(package_cost_cents)
            within_package_budget: bool | None = (
                Decimal(package_cost_cents) / 100
                <= Decimal(str(recipe_request["budget"]))
            )
            package_status: Literal["available", "unavailable"] = "available"
        else:
            package_cost = None
            within_package_budget = None
            package_status = "unavailable"

        results.append(
            {
                "name": generated_recipe["name"],
                "ingredients": priced_ingredients,
                **cost_summary,
                "additional_package_purchase_cost": package_cost,
                "within_package_budget": within_package_budget,
                "package_purchase_status": package_status,
            }
        )

    return {"recipes": results}


def _package_purchase_info(
    quote: GroceryPriceQuote,
    requirement: IngredientRequirement,
    is_owned: bool,
) -> PackagePurchaseInfo:
    package_info: PackagePurchaseInfo = {
        "status": "unavailable",
        "source": quote.source,
        "selected_product": quote.selected_product,
        "product_id": quote.product_id,
        "package_price": quote.package_price,
        "package_quantity": quote.package_quantity,
        "package_unit": quote.package_unit,
        "currency": quote.currency,
        "packages_required": None,
        "purchase_cost": None,
    }

    if is_owned:
        return {
            **package_info,
            "status": "not_required",
            "packages_required": 0,
            "purchase_cost": 0.0,
        }

    if (
        quote.package_price is None
        or quote.package_quantity is None
        or quote.package_unit is None
        or not quote.selected_product
        or quote.currency != "USD"
    ):
        return package_info

    try:
        package_count = whole_packages_required(
            requirement["quantity"],
            requirement["unit"],
            quote.package_quantity,
            quote.package_unit,
        )
        package_price_cents = _price_to_cents(quote.package_price)
    except (ArithmeticError, OverflowError, ValueError):
        return package_info

    purchase_cost = _dollars_from_cents(package_price_cents * package_count)
    return {
        **package_info,
        "status": "available",
        "packages_required": package_count,
        "purchase_cost": purchase_cost,
    }
