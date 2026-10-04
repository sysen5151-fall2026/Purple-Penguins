"""App orchestrator for Chapter 2 walking skeleton.

Implements UC.1 baseline scenario per docs/walking-skeleton.md.
Sequence: User → App → LLM API → Grocery Store → LLM API → App → User.
"""

from user_interface import (
    request_login_info,
    request_ingredients,
    request_budget,
    request_dietary_restrictions,
    display_recipe_and_pricing,
)
from llm_api_interface import send_recipe_requirements, request_pricing


def run_baseline_scenario():
    """Execute the complete UC.1 baseline scenario (17 calls)."""
    # Call 1: User → App: Open App (app.py is started)
    print("Opening app...\n")
    
    # Call 2-3: App → User: Request Login Info; User → App: Provide Login Info
    login_info = request_login_info()
    
    # Call 4: App → User: Approve Login
    print("Login approved.\n")
    
    # Call 5-6: App → User: Request Ingredients; User → App: Provide Ingredients
    ingredients = request_ingredients()
    
    # Call 7-8: App → User: Request Budget; User → App: Provide Budget
    budget = request_budget()
    
    # Call 9-10: App → User: Request Dietary Restrictions; User → App: Provide Dietary Restrictions
    dietary_restrictions = request_dietary_restrictions()
    
    # Call 11-12: App → LLM API: Send Recipe Requirements; LLM API → App: Generate Recipes
    recipes = send_recipe_requirements(
        ingredients=ingredients,
        budget=budget,
        dietary_restrictions=dietary_restrictions,
    )
    
    # Call 13-16: App → LLM API: Request Pricing; LLM API → Grocery Store → LLM API → App
    recipes_with_pricing = request_pricing(recipes)
    
    # Call 17: App → User: Display Recipe & Pricing
    display_recipe_and_pricing(recipes_with_pricing)


if __name__ == "__main__":
    run_baseline_scenario()
