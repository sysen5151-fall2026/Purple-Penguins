"""LLM API interface boundary for Chapter 2 walking skeleton.

Handles recipe generation and pricing logic.
Calls include Calls 11-16 of the baseline scenario sequence.
"""

from grocery_store_interface import get_ingredient_pricing


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


def send_recipe_requirements(ingredients, budget, dietary_restrictions):
    """Call 11-12: App → LLM API: Send Recipe Requirements; LLM API → App: Generate Recipes.
    
    Receives recipe requirements and returns hard-coded stub recipes.
    
    Args:
        ingredients: List of available ingredients
        budget: Budget in dollars
        dietary_restrictions: List of dietary restrictions
    
    Returns:
        List of recipe dicts (without pricing).
    """
    # Call 11: App → LLM API: Send Recipe Requirements
    print("[LLM API] Received recipe requirements.")
    print(f"  Available ingredients: {ingredients}")
    print(f"  Budget: ${budget:.2f}")
    print(f"  Dietary restrictions: {dietary_restrictions}")
    print()
    
    # Call 12: LLM API → App: Generate Recipes (stub)
    recipes = _STUB_RECIPES
    print(f"[LLM API] Generated {len(recipes)} stub recipes.")
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

