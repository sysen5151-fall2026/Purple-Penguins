from decimal import Decimal
from pathlib import Path

import pytest

import app
import recipe_service

from grocery_store_interface import (
    GroceryPricingError,
    get_ingredient_pricing,
    using_grocery_pricing_mode,
)
from grocery_store_interface.html_parser import parse_product_listing_html
from grocery_store_interface.product_extraction import (
    extract_product_candidates,
)
from grocery_store_interface.product_matching import select_product_offer
from grocery_store_interface.retrieval import FixturePageRetriever
from pricing_timing import PricingMeasurement, activate_measurement


FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "grocery_store_interface"
    / "fixtures"
)


def _price_from_fixture(
    fixture_name: str,
    ingredient: str,
    quantity: float = 16.0,
    unit: str = "oz",
):
    with using_grocery_pricing_mode("html_fixture"):
        return get_ingredient_pricing(
            [{"name": ingredient, "quantity": quantity, "unit": unit}],
            page_retriever=FixturePageRetriever(FIXTURE_DIR / fixture_name),
        )


def test_saved_html_fixture_extracts_product_price_and_package():
    quote = _price_from_fixture("product-search.html", "chicken")[
        ("chicken", 16.0, "oz")
    ]

    assert quote.source == "html_fixture"
    assert quote.selected_product == "Chicken Breast"
    assert quote.product_id == "fixture-chicken-001"
    assert quote.ingredient_use_cost == 3.99
    assert quote.package_price == 7.98
    assert quote.package_quantity == 2.0
    assert quote.package_unit == "lb"
    assert quote.currency == "USD"


@pytest.mark.parametrize(
    "ingredient",
    ["rice", "chicken", "milk"],
)
def test_matching_rejects_unrelated_product_types(ingredient):
    with pytest.raises(GroceryPricingError) as error:
        _price_from_fixture(
            "unrelated-products.html",
            ingredient,
        )

    assert "could not be matched reliably" in error.value.public_message


def test_matching_selects_comparable_product_identities_deterministically():
    quote = _price_from_fixture("ambiguous-products.html", "chicken")[
        ("chicken", 16.0, "oz")
    ]

    assert quote.product_id == "fixture-chicken-a"
    assert quote.package_quantity == 1.0
    assert quote.package_price == 4.99


def test_missing_product_price_fails_instead_of_fabricating_a_value():
    with pytest.raises(GroceryPricingError) as error:
        _price_from_fixture("missing-price.html", "chicken")

    assert error.value.status_code == 503
    assert "price or package quantity is missing" in error.value.public_message


def test_unsupported_html_structure_fails_as_malformed_listing():
    with pytest.raises(GroceryPricingError) as error:
        _price_from_fixture("malformed-page.html", "chicken")

    assert error.value.status_code == 502
    assert "expected HTML format" in error.value.public_message


def test_compatible_package_variants_use_deterministic_outlay_rule():
    html = (FIXTURE_DIR / "package-variants.html").read_text(
        encoding="utf-8"
    )
    candidates = extract_product_candidates(
        parse_product_listing_html(html)
    )

    offer = select_product_offer(
        candidates,
        "chicken",
        16.0,
        "oz",
    )

    assert offer.candidate.item_id == "fixture-1lb"
    assert offer.normalized_use_cost == Decimal("3.99")


def test_incompatible_package_units_fail_explicitly():
    with pytest.raises(GroceryPricingError) as error:
        _price_from_fixture(
            "incompatible-package.html",
            "chicken",
        )

    assert "package unit is incompatible" in error.value.public_message


def test_v1_and_v2_keep_cost_contracts_with_fixture_package_data(
    monkeypatch,
):
    recipe = {
        "name": "Fixture Chicken Dinner",
        "ingredients": [
            {"name": "chicken", "quantity": 40.0, "unit": "oz"},
        ],
    }
    monkeypatch.setattr(
        recipe_service,
        "send_recipe_requirements",
        lambda **_kwargs: [recipe],
    )
    client = app.create_app({"TESTING": True}).test_client()

    with using_grocery_pricing_mode("html_fixture"):
        v1 = client.post(
            "/api/v1/recipes",
            json={
                "ingredients": ["salt"],
                "budget": 10.0,
                "dietary_restrictions": [],
            },
        )
        v2 = client.post(
            "/api/v2/recipes",
            json={
                "ingredients": ["salt"],
                "budget": 10.0,
                "dietary_restrictions": [],
            },
        )

    v1_recipe = v1.get_json()["recipes"][0]
    v2_recipe = v2.get_json()["recipes"][0]
    assert set(v1_recipe) == {
        "name",
        "ingredients",
        "estimated_total_cost",
        "additional_purchase_cost",
        "within_budget",
    }
    assert v1_recipe["estimated_total_cost"] == 9.98
    assert v1_recipe["within_budget"] is True
    assert v2_recipe["estimated_total_cost"] == 9.98
    assert v2_recipe["additional_package_purchase_cost"] == 15.96
    assert v2_recipe["within_budget"] is True
    assert v2_recipe["within_package_budget"] is False
    assert v2_recipe["ingredients"][0]["package_purchase"] == {
        "status": "available",
        "source": "html_fixture",
        "selected_product": "Chicken Breast",
        "product_id": "fixture-chicken-001",
        "package_price": 7.98,
        "package_quantity": 2.0,
        "package_unit": "lb",
        "currency": "USD",
        "packages_required": 2,
        "purchase_cost": 15.96,
    }


def test_live_html_mode_is_disabled_before_any_retrieval():
    class ForbiddenRetriever:
        def retrieve_page(self, _ingredient):
            pytest.fail("Live HTML retrieval must remain disabled.")

    with (
        using_grocery_pricing_mode("html_live"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing(
            [{"name": "chicken", "quantity": 16.0, "unit": "oz"}],
            page_retriever=ForbiddenRetriever(),
        )

    assert "disabled until an authorized source is approved" in (
        error.value.public_message
    )


def test_html_pricing_emits_separate_local_timing_stages():
    measurement = PricingMeasurement(
        "actual_html_fixture_pricing",
        "html_fixture",
        "test",
    )
    with using_grocery_pricing_mode("html_fixture"), activate_measurement(
        measurement
    ):
        _price_from_fixture(
            "product-search.html",
            "chicken",
        )

    stages = {timing.stage for timing in measurement.stage_timings}
    assert {
        "fixture_page_retrieval",
        "html_parsing",
        "product_extraction",
        "product_matching",
        "price_extraction",
        "unit_package_normalization",
    }.issubset(stages)
