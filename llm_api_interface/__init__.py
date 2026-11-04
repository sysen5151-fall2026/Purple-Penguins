"""LLM API boundary for the Chapter 2 workflow and configurable generation.

Recipe pricing remains a separate operation delegated to the deterministic
grocery-store interface. Calls include Calls 11-16 of the baseline sequence.
"""

import copy
import os

from grocery_store_interface import get_ingredient_pricing

from .errors import RecipeGenerationServiceError


# Hard-coded stub recipes (Call 12: LLM API → App: Generate Recipes)
_STUB_RECIPES = [
    {
        "name": "Pasta Carbonara",
        "ingredients": ["pasta", "eggs", "bacon"],
    },
    {
        "name": "Vegetable Stir-Fry",
        "ingredients": ["broccoli", "bell peppers", "onions", "soy sauce"],
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
    
    Requests pricing for recipes, calls Grocery Store stub, and returns recipes with pricing.
    
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


def get_pricing(recipes):
    """Internal helper: calls Grocery Store stub and processes pricing for recipes.
    
    Implements Calls 14-16 of the sequence (internal to request_pricing).
    
    Args:
        recipes: List of recipe dicts with ingredients list
    
    Returns:
        List of recipes with pricing data added.
    """
    # Call 14: LLM API → Grocery Store: Retrieve Prices
    all_ingredients = set()
    for recipe in recipes:
        all_ingredients.update(recipe["ingredients"])
    
    print("[LLM API] Requesting pricing from Grocery Store...")
    # Call 15: Grocery Store → LLM API: Provide Pricing
    pricing = get_ingredient_pricing(list(all_ingredients))
    print("[LLM API] Received pricing data.")
    print()
    
    # Call 16: Process and attach pricing to recipes
    recipes_with_pricing = []
    for recipe in recipes:
        total_cost = 0.0
        recipe_with_pricing = {
            "name": recipe["name"],
            "ingredients": {},
        }
        for ingredient in recipe["ingredients"]:
            price = pricing.get(ingredient, 0.0)
            recipe_with_pricing["ingredients"][ingredient] = price
            total_cost += price
        recipe_with_pricing["total_cost"] = total_cost
        recipes_with_pricing.append(recipe_with_pricing)
    
    return recipes_with_pricing
