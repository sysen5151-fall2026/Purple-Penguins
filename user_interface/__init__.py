"""User interface boundary for Chapter 2 walking skeleton.

Handles all User → App and App → User interactions.
"""


def request_login_info():
    """Call 2-3: App → User request login; User → App provide login.
    
    Returns login info stub (no real authentication).
    """
    print("Request: Please enter your login information.")
    username = input("  Username: ")
    password = input("  Password: ")
    print()
    return {"username": username, "password": password}


def request_ingredients():
    """Call 5-6: App → User request ingredients; User → App provide ingredients.
    
    Returns ingredients list stub.
    """
    print("Request: Enter ingredients you have available (comma-separated).")
    ingredients_input = input("  Ingredients: ")
    ingredients = [ing.strip() for ing in ingredients_input.split(",")]
    print()
    return ingredients


def request_budget():
    """Call 7-8: App → User request budget; User → App provide budget.
    
    Returns budget stub.
    """
    print("Request: Enter your budget (in dollars).")
    budget_input = input("  Budget: $")
    budget = float(budget_input)
    print()
    return budget


def request_dietary_restrictions():
    """Call 9-10: App → User request dietary restrictions; User → App provide restrictions.
    
    Returns dietary restrictions stub.
    """
    print("Request: Enter any dietary restrictions (comma-separated).")
    restrictions_input = input("  Restrictions: ")
    restrictions = [r.strip() for r in restrictions_input.split(",")] if restrictions_input.strip() else []
    print()
    return restrictions


def display_recipe_and_pricing(recipes_with_pricing):
    """Call 17: App → User: Display Recipe & Pricing.
    
    Displays the final hard-coded recipe and pricing result.
    """
    print("\n" + "="*60)
    print("RECIPE & PRICING RESULT")
    print("="*60)
    for recipe in recipes_with_pricing:
        print(f"\nRecipe: {recipe['name']}")
        print(f"Total Cost: ${recipe['total_cost']:.2f}")
        print(f"Ingredients:")
        for ingredient, price in recipe['ingredients'].items():
            print(f"  - {ingredient}: ${price:.2f}")
    print("\n" + "="*60)

