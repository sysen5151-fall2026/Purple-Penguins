"""Grocery Store interface boundary for Chapter 2 walking skeleton.

Handles Call 14-15: LLM API requests pricing; Grocery Store returns hard-coded pricing.
No real web scraping or external access.
"""

# Hard-coded stub ingredient pricing (Call 15: Grocery Store → LLM API: Provide Pricing)
_STUB_PRICING = {
    "pasta": 1.99,
    "eggs": 3.49,
    "bacon": 5.99,
    "broccoli": 2.49,
    "bell peppers": 1.99,
    "onions": 0.99,
    "soy sauce": 2.99,
}


def get_ingredient_pricing(ingredients):
    """Call 14-15: LLM API → Grocery Store: Retrieve Prices; Grocery Store → LLM API: Provide Pricing.
    
    Returns hard-coded deterministic pricing for ingredients.
    No real web scraping or external API calls.
    
    Args:
        ingredients: List of ingredient names
    
    Returns:
        Dict mapping ingredient name to price in dollars.
    """
    print(f"[Grocery Store] Received pricing request for {len(ingredients)} ingredients.")
    
    pricing = {}
    for ingredient in ingredients:
        # Return stub price or default
        pricing[ingredient] = _STUB_PRICING.get(ingredient, 1.00)
    
    print(f"[Grocery Store] Returning pricing data ({len(pricing)} items).")
    print()
    
    return pricing

