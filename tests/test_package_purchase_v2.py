from copy import deepcopy

import app
import recipe_service
from grocery_store_interface.models import GroceryPriceQuote


_REQUIREMENT = {
    "name": "chicken breast",
    "quantity": 16.0,
    "unit": "oz",
}
_QUOTE = GroceryPriceQuote(
    ingredient_use_cost=2.49,
    source="html_fixture",
    selected_product="Chicken Breast",
    package_price=4.98,
    package_quantity=2.0,
    package_unit="lb",
    currency="USD",
)


def install_single_recipe(monkeypatch, quote, requirement=None, recipe_count=1):
    ingredient = requirement or _REQUIREMENT
    recipes = [
        {
            "name": f"Recipe {index + 1}",
            "ingredients": [deepcopy(ingredient)],
        }
        for index in range(recipe_count)
    ]
    priced_recipes = [
        {
            "name": recipe["name"],
            "ingredients": {ingredient["name"]: quote.ingredient_use_cost},
            "quotes": {ingredient["name"]: quote},
            "total_cost": quote.ingredient_use_cost,
        }
        for recipe in recipes
    ]
    monkeypatch.setattr(
        recipe_service,
        "send_recipe_requirements",
        lambda **_kwargs: recipes,
    )
    monkeypatch.setattr(
        recipe_service,
        "request_pricing_with_quotes",
        lambda _recipes: priced_recipes,
    )


def post_v2(client, *, owned, budget):
    return client.post(
        "/api/v2/recipes",
        json={
            "ingredients": owned,
            "budget": budget,
            "dietary_restrictions": [],
        },
    )


def test_v2_separates_recipe_use_cost_from_full_package_purchase_cost(
    monkeypatch,
):
    install_single_recipe(monkeypatch, _QUOTE)
    client = app.create_app({"TESTING": True}).test_client()

    response = post_v2(client, owned=["salt"], budget=3.0)

    recipe = response.get_json()["recipes"][0]
    assert response.status_code == 200
    assert set(recipe) == {
        "name",
        "ingredients",
        "estimated_total_cost",
        "additional_purchase_cost",
        "within_budget",
        "additional_package_purchase_cost",
        "within_package_budget",
        "package_purchase_status",
    }
    assert recipe["estimated_total_cost"] == 2.49
    assert recipe["additional_purchase_cost"] == 2.49
    assert recipe["within_budget"] is True
    assert recipe["additional_package_purchase_cost"] == 4.98
    assert recipe["within_package_budget"] is False
    assert recipe["package_purchase_status"] == "available"
    assert recipe["ingredients"][0]["package_purchase"] == {
        "status": "available",
        "source": "html_fixture",
        "selected_product": "Chicken Breast",
        "product_id": None,
        "package_price": 4.98,
        "package_quantity": 2.0,
        "package_unit": "lb",
        "currency": "USD",
        "packages_required": 1,
        "purchase_cost": 4.98,
    }


def test_v2_rounds_package_count_up_for_more_than_one_package(monkeypatch):
    requirement = {
        "name": "chicken breast",
        "quantity": 40.0,
        "unit": "oz",
    }
    quote = GroceryPriceQuote(
        ingredient_use_cost=6.22,
        source="html_fixture",
        selected_product="Chicken Breast",
        package_price=4.98,
        package_quantity=2.0,
        package_unit="lb",
        currency="USD",
    )
    install_single_recipe(monkeypatch, quote, requirement)

    response = post_v2(
        app.create_app({"TESTING": True}).test_client(),
        owned=["salt"],
        budget=9.0,
    )

    recipe = response.get_json()["recipes"][0]
    assert recipe["ingredients"][0]["package_purchase"]["packages_required"] == 2
    assert recipe["additional_package_purchase_cost"] == 9.96
    assert recipe["within_package_budget"] is False


def test_v2_excludes_owned_items_from_package_purchase_cost(monkeypatch):
    install_single_recipe(monkeypatch, _QUOTE)
    client = app.create_app({"TESTING": True}).test_client()

    recipe = post_v2(client, owned=["Chicken Breast"], budget=0.01).get_json()[
        "recipes"
    ][0]

    assert recipe["ingredients"][0]["owned"] is True
    assert recipe["additional_purchase_cost"] == 0
    assert recipe["additional_package_purchase_cost"] == 0
    assert recipe["within_package_budget"] is True
    assert recipe["ingredients"][0]["package_purchase"]["status"] == "not_required"


def test_v2_reports_package_cost_unavailable_in_stub_mode(monkeypatch):
    quote = GroceryPriceQuote(
        ingredient_use_cost=1.99,
        source="stub",
    )
    install_single_recipe(monkeypatch, quote)

    recipe = post_v2(
        app.create_app({"TESTING": True}).test_client(),
        owned=["salt"],
        budget=10,
    ).get_json()["recipes"][0]

    assert recipe["additional_purchase_cost"] == 1.99
    assert recipe["package_purchase_status"] == "unavailable"
    assert recipe["additional_package_purchase_cost"] is None
    assert recipe["within_package_budget"] is None
    assert recipe["ingredients"][0]["package_purchase"]["purchase_cost"] is None


def test_v2_calculates_each_recipe_as_an_alternative_not_a_combined_cart(
    monkeypatch,
):
    install_single_recipe(monkeypatch, _QUOTE, recipe_count=2)

    recipes = post_v2(
        app.create_app({"TESTING": True}).test_client(),
        owned=["salt"],
        budget=10,
    ).get_json()["recipes"]

    assert len(recipes) == 2
    assert [
        recipe["additional_package_purchase_cost"] for recipe in recipes
    ] == [4.98, 4.98]
