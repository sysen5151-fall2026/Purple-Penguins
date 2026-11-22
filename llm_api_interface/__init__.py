"""LLM API boundary for the Chapter 2 workflow and configurable generation.

Recipe pricing remains a separate operation delegated to the deterministic
grocery-store interface. Calls include Calls 11-16 of the baseline sequence.
"""

import copy
import os

from grocery_store_interface import get_ingredient_pricing
from grocery_store_interface.models import requirement_key
from pricing_timing import measure_stage

from .errors import RecipeGenerationServiceError


# Hard-coded stub recipes (Call 12: LLM API → App: Generate Recipes)
_STUB_RECIPES = [
    {
        "name": "Pasta Carbonara",
        "ingredients": [
            {"name": "pasta", "quantity": 12.0, "unit": "oz"},
            {"name": "eggs", "quantity": 3.0, "unit": "count"},
            {"name": "bacon", "quantity": 4.0, "unit": "oz"},
        ],
    },
    {
        "name": "Vegetable Stir-Fry",
        "ingredients": [
            {"name": "broccoli", "quantity": 1.0, "unit": "head"},
            {"name": "bell peppers", "quantity": 2.0, "unit": "count"},
            {"name": "onions", "quantity": 1.0, "unit": "count"},
            {"name": "soy sauce", "quantity": 2.0, "unit": "fl_oz"},
        ],
    },
]


def get_recipe_generation_mode() -> str:
    """Return the configured provider mode, defaulting to deterministic stub."""
    return os.getenv("RECIPE_GENERATION_MODE", "stub").strip().casefold()


def send_recipe_requirements(ingredients, budget, dietary_restrictions):
    """F.2.4.4 / C.2.4.4: generate recipes using the configured LLM API.

    The default ``stub`` mode preserves the Chapter 2 walking-skeleton flow.
    Optional ``openai`` mode uses the App-to-LLM API interface and returns
    validated recipe names and ingredient lists without prices.

    Args:
        ingredients: List of available ingredients
        budget: Budget in dollars
        dietary_restrictions: List of dietary restrictions

    Returns:
        List of recipe dicts (without pricing).
    """
    print(
        "[LLM API] Received recipe requirements "
        f"({len(ingredients)} available ingredient(s))."
    )

    mode = get_recipe_generation_mode()
    if mode == "stub":
        recipes = copy.deepcopy(_STUB_RECIPES)
        print(f"[LLM API] Generated {len(recipes)} deterministic stub recipes.")
    elif mode == "openai":
        from .openai_adapter import generate_recipes

        recipes = generate_recipes(
            ingredients=ingredients,
            budget=budget,
            dietary_restrictions=dietary_restrictions,
        )
        print(f"[LLM API] Generated {len(recipes)} OpenAI recipe(s).")
    else:
        raise RecipeGenerationServiceError(
            "Recipe generation is not configured. Please contact the "
            "application administrator.",
            status_code=503,
            log_message=(
                "RECIPE_GENERATION_MODE must be either 'stub' or 'openai'."
            ),
        )
    print()

    return recipes


def request_pricing(recipes):
    """Call 13-16: App → LLM API: Request Pricing; LLM API → Grocery Store → LLM API → App.
    
    Requests prices for recipe quantity requirements and returns normalized costs.
    
    Args:
        recipes: List of recipe dicts (without pricing)
    
    Returns:
        List of recipe dicts with pricing attached.
    """
    # Call 13: App → LLM API: Request Pricing
    print("[LLM API] Received pricing request for recipes.")
    print()
    
    # Calls 14-15: LLM API → Grocery Store → LLM API
    recipes_with_pricing = get_pricing(recipes)
    
    # Call 16: LLM API → App: Process Ingredient Pricing
    print("[LLM API] Processed ingredient pricing.")
    print()
    
    return recipes_with_pricing


def request_pricing_with_quotes(recipes):
    """Return price quotes with product/package provenance for API v2."""
    print("[LLM API] Received pricing request for recipes.")
    print()
    recipes_with_quotes = get_pricing_with_quotes(recipes)
    print("[LLM API] Processed ingredient pricing.")
    print()
    return recipes_with_quotes


def get_pricing(recipes):
    """Request ingredient prices and process them for each recipe.
    
    Implements Calls 14-16 of the sequence (internal to request_pricing).
    
    Args:
        recipes:         List of recipe dicts with quantity-bearing ingredient requirements
    
    Returns:
        List of recipes with pricing data added.
    """
    recipes_with_quotes = _get_pricing_with_quotes(recipes)
    return [
        {
            "name": recipe["name"],
            "ingredients": {
                name: quote.ingredient_use_cost
                for name, quote in recipe["quotes"].items()
            },
            "total_cost": recipe["total_cost"],
        }
        for recipe in recipes_with_quotes
    ]


def get_pricing_with_quotes(recipes):
    """Return recipe cost data and the associated source/package quotes."""
    return _get_pricing_with_quotes(recipes)


def _get_pricing_with_quotes(recipes):
    # Call 14: LLM API → Grocery Store: Retrieve Prices
    with measure_stage("pricing_request_preparation"):
        all_ingredients = {}
        for recipe in recipes:
            for requirement in recipe["ingredients"]:
                all_ingredients.setdefault(
                    requirement_key(requirement),
                    requirement,
                )
        ingredient_requirements = list(all_ingredients.values())

    print("[LLM API] Requesting pricing from Grocery Store...")
    # Call 15: Grocery Store → LLM API: Provide Pricing
    pricing = get_ingredient_pricing(ingredient_requirements)
    print("[LLM API] Received pricing data.")
    print()

    # Call 16: Process and attach pricing to recipes
    with measure_stage("pricing_response_processing"):
        recipes_with_pricing = []
        for recipe in recipes:
            total_cost = 0.0
            ingredient_quotes = {}
            recipe_with_pricing = {
                "name": recipe["name"],
                "ingredients": {},
            }
            for requirement in recipe["ingredients"]:
                ingredient = requirement["name"]
                quote = pricing[requirement_key(requirement)]
                price = quote.ingredient_use_cost
                ingredient_quotes[ingredient] = quote
                recipe_with_pricing["ingredients"][ingredient] = price
                total_cost += price
            recipe_with_pricing["total_cost"] = total_cost
            recipe_with_pricing["quotes"] = ingredient_quotes
            recipes_with_pricing.append(recipe_with_pricing)

    return recipes_with_pricing
