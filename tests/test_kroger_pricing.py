import base64
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import app
import pytest
import recipe_service

from grocery_store_interface import (
    GroceryPricingError,
    get_ingredient_pricing,
    using_grocery_pricing_mode,
)
from grocery_store_interface.kroger_api import (
    _NoRedirectHandler,
)
from grocery_store_interface.models import GroceryPriceQuote
from pricing_timing import (
    PricingMeasurement,
    activate_measurement,
    record_external_request,
)
from scripts import smoke_test_kroger


_REQUIREMENT = {
    "name": "chicken breast",
    "quantity": 16.0,
    "unit": "oz",
}
_TOKEN = {"access_token": "test-token", "expires_in": 1800}


def _product(
    *,
    product_id="chicken-001",
    description="Chicken Breast",
    categories=None,
    size="2 lb",
    regular=7.98,
    promo=0,
    sold_by="Unit",
):
    return {
        "productId": product_id,
        "description": description,
        "brand": "Test Brand",
        "categories": categories or ["Meat"],
        "items": [
            {
                "itemId": f"{product_id}-item",
                "price": {"regular": regular, "promo": promo},
                "size": size,
                "soldBy": sold_by,
            }
        ],
    }


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.payload


class RawResponse(FakeResponse):
    def __init__(self, body):
        self.payload = body


def _set_kroger_environment(monkeypatch):
    monkeypatch.setenv("GROCERY_PRICING_MODE", "kroger")
    monkeypatch.setenv("KROGER_CLIENT_ID", "client-id")
    monkeypatch.setenv("KROGER_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("KROGER_LOCATION_ID", "01400943")


def _install_responses(monkeypatch, responses):
    calls = []
    monkeypatch.setattr(
        "grocery_store_interface.kroger_api._pace_requests",
        lambda: None,
    )

    def fake_open(request, *, timeout_seconds):
        calls.append((request, timeout_seconds))
        response = responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    monkeypatch.setattr(
        "grocery_store_interface.kroger_api._open_request",
        fake_open,
    )
    return calls


def _pricing_response(product=None):
    return {"data": [product or _product()]}


def test_kroger_oauth_and_location_filtered_product_search(monkeypatch):
    _set_kroger_environment(monkeypatch)
    calls = _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response())],
    )

    with using_grocery_pricing_mode("kroger"):
        quote = get_ingredient_pricing([_REQUIREMENT])[
            ("chicken breast", 16.0, "oz")
        ]

    assert quote.source == "kroger"
    assert quote.selected_product == "Chicken Breast"
    assert quote.product_id == "chicken-001"
    assert quote.ingredient_use_cost == 3.99
    assert quote.package_price == 7.98
    assert quote.package_quantity == 2.0
    assert quote.package_unit == "lb"
    assert quote.currency == "USD"
    assert len(calls) == 2
    token_request, token_timeout = calls[0]
    search_request, search_timeout = calls[1]
    assert token_timeout == search_timeout == 10.0
    assert token_request.full_url.endswith("/connect/oauth2/token")
    assert token_request.get_method() == "POST"
    assert token_request.get_header("Authorization") == (
        "Basic " + base64.b64encode(b"client-id:client-secret").decode("ascii")
    )
    assert token_request.data == (
        b"grant_type=client_credentials&scope=product.compact"
    )
    query = parse_qs(urlparse(search_request.full_url).query)
    assert query == {
        "filter.term": ["chicken breast"],
        "filter.locationId": ["01400943"],
        "filter.limit": ["20"],
    }
    assert search_request.get_header("Authorization") == "Bearer test-token"


@pytest.mark.parametrize(
    ("ingredient_name", "quantity", "unit", "description", "size", "category"),
    [
        ("unsalted butter", 8.0, "oz", "Unsalted Butter", "1 lb", "Dairy"),
        (
            "dry angel hair pasta",
            8.0,
            "oz",
            "Dry Angel Hair Pasta",
            "1 lb",
            "Pasta",
        ),
        (
            "canned diced tomatoes",
            8.0,
            "oz",
            "Canned Diced Tomatoes",
            "14.5 oz",
            "Canned Vegetables",
        ),
        ("whole milk", 1.0, "cup", "Whole Milk", "1 gal", "Dairy"),
    ],
)
def test_kroger_search_uses_specific_generated_ingredient_name(
    monkeypatch,
    ingredient_name,
    quantity,
    unit,
    description,
    size,
    category,
):
    _set_kroger_environment(monkeypatch)
    product = _product(
        product_id="matched-product",
        description=description,
        categories=[category],
        size=size,
    )
    calls = _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with using_grocery_pricing_mode("kroger"):
        get_ingredient_pricing(
            [{"name": ingredient_name, "quantity": quantity, "unit": unit}]
        )

    query = parse_qs(urlparse(calls[1][0].full_url).query)
    assert query["filter.term"] == [ingredient_name]


def test_kroger_http_and_extraction_stages_are_timed(monkeypatch):
    _set_kroger_environment(monkeypatch)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response())],
    )
    measurement = PricingMeasurement(
        "actual_kroger_api_pricing",
        "kroger",
        "test",
    )

    with using_grocery_pricing_mode("kroger"), activate_measurement(
        measurement
    ):
        get_ingredient_pricing([_REQUIREMENT])

    stages = [timing.stage for timing in measurement.stage_timings]
    assert stages.count("kroger_http_request") == 2
    assert stages.count("kroger_response_parsing") == 2
    assert "kroger_product_extraction" in stages
    assert "product_matching" in stages
    assert "price_extraction" in stages
    assert measurement.provider_request_count == 2


def test_kroger_client_does_not_follow_redirects():
    redirect = _NoRedirectHandler().redirect_request(
        Request("https://api.kroger.com/v1/products"),
        None,
        302,
        "redirect",
        {},
        "https://example.com/redirected",
    )

    assert redirect is None


def test_kroger_uses_promotional_price_when_lower(monkeypatch):
    _set_kroger_environment(monkeypatch)
    product = _product(regular=8.98, promo=6.98)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with using_grocery_pricing_mode("kroger"):
        quote = get_ingredient_pricing([_REQUIREMENT])[
            ("chicken breast", 16.0, "oz")
        ]

    assert quote.package_price == 6.98
    assert quote.ingredient_use_cost == 3.49


@pytest.mark.parametrize(
    ("description", "product_id"),
    [
        ("Spaghetti", "spaghetti"),
        ("Penne", "penne"),
        ("Pasta", "pasta"),
    ],
)
def test_pasta_matches_controlled_aliases_and_repeated_category(
    monkeypatch,
    description,
    product_id,
):
    _set_kroger_environment(monkeypatch)
    product = _product(
        product_id=product_id,
        description=description,
        categories=["Pasta"],
        size="1 lb",
        regular=4.49,
    )
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )
    requirement = {"name": "pasta", "quantity": 16.0, "unit": "oz"}

    with using_grocery_pricing_mode("kroger"):
        quote = get_ingredient_pricing([requirement])[
            ("pasta", 16.0, "oz")
        ]

    assert quote.selected_product == description
    assert quote.product_id == product_id
    assert quote.ingredient_use_cost == 4.49


def test_pasta_category_does_not_override_contradictory_product_name(
    monkeypatch,
):
    _set_kroger_environment(monkeypatch)
    product = _product(
        product_id="rice-product",
        description="Rice",
        categories=["Pasta"],
    )
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing(
            [{"name": "pasta", "quantity": 16.0, "unit": "oz"}]
        )

    assert "could not be matched reliably" in error.value.public_message
    assert "failure_category=no_confident_match" in error.value.log_message


def test_kroger_selects_comparable_pasta_without_cheapest_price_ranking(
    monkeypatch,
    caplog,
):
    caplog.set_level(
        "INFO",
        logger="grocery_store_interface.product_matching",
    )
    _set_kroger_environment(monkeypatch)
    products = [
        _product(
            product_id="organic-pasta",
            description="Organic Spaghetti",
            categories=["Pasta"],
            size="1 lb",
            regular=0.49,
        ),
        _product(
            product_id="bulk-penne",
            description="Penne",
            categories=["Pasta"],
            size="2 lb",
            regular=1.00,
        ),
        _product(
            product_id="standard-spaghetti",
            description="Spaghetti",
            categories=["Pasta"],
            size="1 lb",
            regular=4.99,
        ),
    ]
    products[0]["brand"] = "Organic Brand"
    products[1]["brand"] = "Brand B"
    products[2]["brand"] = "Brand A"
    requirement = {"name": "pasta", "quantity": 16.0, "unit": "oz"}

    def run(candidates):
        _install_responses(
            monkeypatch,
            [FakeResponse(_TOKEN), FakeResponse({"data": candidates})],
        )
        with using_grocery_pricing_mode("kroger"):
            return get_ingredient_pricing([requirement])[
                ("pasta", 16.0, "oz")
            ]

    first = run(products)
    second = run(list(reversed(products)))

    assert first.product_id == second.product_id == "standard-spaghetti"
    assert first.selected_product == second.selected_product == "Spaghetti"
    assert first.package_price == 4.99
    assert first.ingredient_use_cost == 4.99
    assert "candidate_count=3" in caplog.text
    assert "relevance_count=3" in caplog.text
    assert "eligible_priceable_count=3" in caplog.text
    assert "selected_product_id='standard-spaghetti'" in caplog.text
    assert "selection_policy_reason=preferred_standard_variant" in caplog.text


def test_kroger_selects_angel_hair_across_valid_brands_deterministically(
    monkeypatch,
):
    _set_kroger_environment(monkeypatch)
    products = [
        _product(
            product_id="brand-b-angel-hair",
            description="Angel Hair Pasta",
            categories=["Pasta"],
            size="1 lb",
            regular=2.49,
        ),
        _product(
            product_id="brand-a-angel-hair",
            description="Angel Hair Pasta",
            categories=["Pasta"],
            size="1 lb",
            regular=4.99,
        ),
    ]
    products[0]["brand"] = "Brand B"
    products[1]["brand"] = "Brand A"
    requirement = {
        "name": "angel hair pasta",
        "quantity": 8.0,
        "unit": "oz",
    }

    def run(candidates):
        _install_responses(
            monkeypatch,
            [FakeResponse(_TOKEN), FakeResponse({"data": candidates})],
        )
        with using_grocery_pricing_mode("kroger"):
            return get_ingredient_pricing([requirement])[
                ("angel hair pasta", 8.0, "oz")
            ]

    first = run(products)
    second = run(list(reversed(products)))

    assert first.product_id == second.product_id == "brand-a-angel-hair"
    assert first.package_price == second.package_price == 4.99


@pytest.mark.parametrize(
    "description",
    ["Pasta Sauce", "Pasta Meal", "Prepared Pasta"],
)
def test_kroger_excludes_pasta_sauce_and_prepared_products(
    monkeypatch,
    description,
):
    _set_kroger_environment(monkeypatch)
    product = _product(
        product_id="prepared-pasta",
        description=description,
        categories=["Pasta"],
    )
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing(
            [{"name": "pasta", "quantity": 16.0, "unit": "oz"}]
        )

    assert "failure_category=no_confident_match" in error.value.log_message


def test_controlled_alias_does_not_override_spaghetti_squash_description(
    monkeypatch,
):
    _set_kroger_environment(monkeypatch)
    product = _product(
        product_id="squash-product",
        description="Spaghetti Squash",
        categories=["Produce"],
    )
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing(
            [{"name": "pasta", "quantity": 16.0, "unit": "oz"}]
        )

    assert "failure_category=no_confident_match" in error.value.log_message


def test_explicit_milk_variety_does_not_match_another_form(monkeypatch):
    _set_kroger_environment(monkeypatch)
    products = [
        _product(
            product_id="two-percent-milk",
            description="Kroger 2% Reduced Fat Milk",
            categories=["Dairy"],
            size="1 gal",
            regular=3.19,
        ),
        _product(
            product_id="whole-milk",
            description="Kroger Whole Milk",
            categories=["Dairy"],
            size="1 gal",
            regular=3.49,
        ),
    ]
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse({"data": products})],
    )

    with using_grocery_pricing_mode("kroger"):
        quote = get_ingredient_pricing(
            [{"name": "whole milk", "quantity": 1.0, "unit": "gal"}]
        )[("whole milk", 1.0, "gal")]

    assert quote.selected_product == "Kroger Whole Milk"
    assert quote.product_id == "whole-milk"


def test_explicit_fresh_pasta_form_does_not_match_dry_pasta(monkeypatch):
    _set_kroger_environment(monkeypatch)
    products = [
        _product(
            product_id="fresh-pasta",
            description="Fresh Pasta",
            categories=["Pasta"],
            size="8 oz",
            regular=5.99,
        ),
        _product(
            product_id="dry-pasta",
            description="Dry Pasta",
            categories=["Pasta"],
            size="1 lb",
            regular=1.99,
        ),
    ]
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse({"data": products})],
    )

    with using_grocery_pricing_mode("kroger"):
        quote = get_ingredient_pricing(
            [{"name": "fresh pasta", "quantity": 8.0, "unit": "oz"}]
        )[("fresh pasta", 8.0, "oz")]

    assert quote.product_id == "fresh-pasta"
    assert quote.selected_product == "Fresh Pasta"


@pytest.mark.parametrize(
    ("ingredient", "product"),
    [
        ("rice", _product(description="Rice Pudding", categories=["Dessert"])),
        (
            "chicken",
            _product(description="Chicken Stock", categories=["Soup", "Stock"]),
        ),
        (
            "milk",
            _product(description="Milk Chocolate", categories=["Candy"]),
        ),
    ],
)
def test_kroger_rejects_unrelated_product_categories(
    monkeypatch,
    ingredient,
    product,
):
    _set_kroger_environment(monkeypatch)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing(
            [{"name": ingredient, "quantity": 16.0, "unit": "oz"}]
        )

    assert "could not be matched reliably" in error.value.public_message
    assert "failure_category=no_confident_match" in error.value.log_message
    assert "candidate_count=1" in error.value.log_message
    assert "relevance_count=0" in error.value.log_message


def test_kroger_rejects_genuinely_ambiguous_product_forms(monkeypatch):
    _set_kroger_environment(monkeypatch)
    products = [
        _product(
            product_id="whole-milk",
            description="Whole Milk",
            categories=["Dairy"],
            size="1 gal",
            regular=3.19,
        ),
        _product(
            product_id="evaporated-milk",
            description="Evaporated Milk",
            categories=["Dairy"],
            size="12 fl_oz",
            regular=1.49,
        ),
    ]
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse({"data": products})],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing(
            [{"name": "milk", "quantity": 1.0, "unit": "gal"}]
        )

    assert "more than one materially different" in (
        error.value.public_message.casefold()
    )
    assert "failure_category=ambiguous_match" in error.value.log_message
    assert "candidate_count=2" in error.value.log_message
    assert "relevance_count=2" in error.value.log_message
    assert "eligible_priceable_count=2" in error.value.log_message


def test_kroger_no_candidate_diagnostics_are_internal_and_sanitized(monkeypatch):
    _set_kroger_environment(monkeypatch)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse({"data": []})],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert "failure_category=no_candidates" in error.value.log_message
    assert "requested_ingredient='chicken breast'" in error.value.log_message
    assert "candidate_count=0" in error.value.log_message
    assert "relevance_count=0" in error.value.log_message
    assert "eligible_priceable_count=0" in error.value.log_message
    assert "test-token" not in error.value.log_message
    assert "client-secret" not in error.value.log_message


def test_v2_match_diagnostics_are_logged_but_not_returned_to_client(
    monkeypatch,
    caplog,
):
    _set_kroger_environment(monkeypatch)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse({"data": []})],
    )
    client = app.create_app({"TESTING": True}).test_client()

    response = client.post(
        "/api/v2/recipes",
        json={
            "ingredients": ["milk", "eggs", "pasta", "bread", "cheese"],
            "budget": 20.0,
            "dietary_restrictions": [],
        },
    )

    assert response.status_code == 503
    assert response.get_json() == {
        "error": {
            "code": "backend_failure",
            "message": (
                "A grocery product could not be matched reliably to an "
                "ingredient."
            ),
        }
    }
    assert "failure_category=no_candidates" in caplog.text
    assert "requested_ingredient='pasta'" in caplog.text
    assert "candidate_count=0" in caplog.text
    assert "relevance_count=0" in caplog.text
    assert b"requested_ingredient" not in response.data


@pytest.mark.parametrize(
    "price",
    [
        {"regular": 0, "promo": 0},
        {"regular": "not-a-price", "promo": None},
    ],
)
def test_kroger_rejects_missing_or_malformed_prices(monkeypatch, price):
    _set_kroger_environment(monkeypatch)
    product = _product()
    product["items"][0]["price"] = price
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert "price or package quantity is missing or invalid" in (
        error.value.public_message
    )
    assert "failure_category=invalid_price" in error.value.log_message
    assert "invalid_price_count=1" in error.value.log_message


def test_kroger_rejects_incompatible_package_units(monkeypatch):
    _set_kroger_environment(monkeypatch)
    _install_responses(
        monkeypatch,
        [
            FakeResponse(_TOKEN),
            FakeResponse(_pricing_response(_product(size="16 fl_oz"))),
        ],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert "package unit is incompatible" in error.value.public_message
    assert "failure_category=incompatible_units" in error.value.log_message
    assert "incompatible_units_count=1" in error.value.log_message


def test_kroger_missing_package_data_is_diagnosed_as_invalid_package(
    monkeypatch,
):
    _set_kroger_environment(monkeypatch)
    product = _product(size=None)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert "failure_category=invalid_package" in error.value.log_message
    assert "candidate_count=1" in error.value.log_message
    assert "relevance_count=1" in error.value.log_message
    assert "missing_package_size_count=1" in error.value.log_message


@pytest.mark.parametrize(
    ("size", "sold_by", "diagnostic"),
    [
        ("2 x 8 oz", "Unit", "unsupported_package_size_count=1"),
        (None, "Unit", "missing_package_size_count=1"),
        ("1 lb", "Weight", "non_unit_sold_by_count=1"),
        ("1 lb", None, "missing_sold_by_count=1"),
    ],
)
def test_kroger_package_failure_diagnostics_identify_validation_reason(
    monkeypatch,
    size,
    sold_by,
    diagnostic,
):
    _set_kroger_environment(monkeypatch)
    product = _product(size=size, sold_by=sold_by)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), FakeResponse(_pricing_response(product))],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert "failure_category=invalid_package" in error.value.log_message
    assert diagnostic in error.value.log_message
    if size:
        assert size not in error.value.log_message


def test_kroger_authentication_failure_is_sanitized(monkeypatch):
    _set_kroger_environment(monkeypatch)
    calls = _install_responses(
        monkeypatch,
        [
            HTTPError(
                "https://api.kroger.com/v1/connect/oauth2/token",
                401,
                "unauthorized",
                None,
                None,
            )
        ],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert error.value.status_code == 503
    assert error.value.provider_status_code == 401
    assert "client-secret" not in error.value.log_message
    assert len(calls) == 1


def test_kroger_rate_limit_is_not_retried(monkeypatch):
    _set_kroger_environment(monkeypatch)
    calls = _install_responses(
        monkeypatch,
        [
            FakeResponse(_TOKEN),
            HTTPError(
                "https://api.kroger.com/v1/products",
                429,
                "rate limited",
                None,
                None,
            ),
        ],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert error.value.status_code == 503
    assert error.value.provider_status_code == 429
    assert len(calls) == 2


def test_kroger_timeout_is_not_retried(monkeypatch):
    _set_kroger_environment(monkeypatch)
    calls = _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), TimeoutError("sensitive timeout detail")],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert error.value.status_code == 503
    assert "sensitive timeout detail" not in error.value.log_message
    assert len(calls) == 2


def test_kroger_malformed_json_is_controlled(monkeypatch):
    _set_kroger_environment(monkeypatch)
    _install_responses(
        monkeypatch,
        [FakeResponse(_TOKEN), RawResponse(b"<html>not json</html>")],
    )

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing([_REQUIREMENT])

    assert error.value.status_code == 502
    assert "not json" not in error.value.log_message


def test_kroger_missing_configuration_does_not_fall_back_to_fixture(
    monkeypatch,
):
    monkeypatch.setenv("GROCERY_PRICING_MODE", "kroger")
    monkeypatch.delenv("KROGER_CLIENT_ID", raising=False)
    monkeypatch.delenv("KROGER_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("KROGER_LOCATION_ID", raising=False)
    monkeypatch.setattr(
        "grocery_store_interface.kroger_api._open_request",
        lambda *_args, **_kwargs: pytest.fail("HTTP must not run."),
    )

    with pytest.raises(GroceryPricingError) as error:
        get_ingredient_pricing([_REQUIREMENT])

    assert error.value.status_code == 503
    assert "not configured" in error.value.public_message


def test_kroger_product_search_cap_rejects_before_http(monkeypatch):
    _set_kroger_environment(monkeypatch)
    monkeypatch.setattr(
        "grocery_store_interface.kroger_api._open_request",
        lambda *_args, **_kwargs: pytest.fail("HTTP must not run."),
    )
    requirements = [
        {"name": f"ingredient {number}", "quantity": 1.0, "unit": "count"}
        for number in range(26)
    ]

    with (
        using_grocery_pricing_mode("kroger"),
        pytest.raises(GroceryPricingError) as error,
    ):
        get_ingredient_pricing(requirements)

    assert "too many distinct ingredients" in error.value.public_message


def test_kroger_quotes_preserve_v1_and_v2_cost_contracts(monkeypatch):
    _set_kroger_environment(monkeypatch)
    recipe = {
        "name": "Kroger Chicken Dinner",
        "ingredients": [
            {"name": "chicken breast", "quantity": 40.0, "unit": "oz"},
        ],
    }
    monkeypatch.setattr(
        recipe_service,
        "send_recipe_requirements",
        lambda **_kwargs: [recipe],
    )
    product = _product()
    responses = [
        FakeResponse(_TOKEN),
        FakeResponse(_pricing_response(product)),
        FakeResponse(_TOKEN),
        FakeResponse(_pricing_response(product)),
    ]
    calls = _install_responses(monkeypatch, responses)
    client = app.create_app({"TESTING": True}).test_client()

    with using_grocery_pricing_mode("kroger"):
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
    assert v2_recipe["within_package_budget"] is False
    assert v2_recipe["ingredients"][0]["package_purchase"] == {
        "status": "available",
        "source": "kroger",
        "selected_product": "Chicken Breast",
        "product_id": "chicken-001",
        "package_price": 7.98,
        "package_quantity": 2.0,
        "package_unit": "lb",
        "currency": "USD",
        "packages_required": 2,
        "purchase_cost": 15.96,
    }
    assert len(calls) == 4


def test_kroger_representative_selection_preserves_v1_v2_pricing_and_provenance(
    monkeypatch,
):
    _set_kroger_environment(monkeypatch)
    recipe = {
        "name": "Chicken Dinner",
        "ingredients": [
            {"name": "chicken breast", "quantity": 16.0, "unit": "oz"},
        ],
    }
    monkeypatch.setattr(
        recipe_service,
        "send_recipe_requirements",
        lambda **_kwargs: [recipe],
    )
    products = [
        _product(
            product_id="lower-priced-brand",
            description="Chicken Breast",
            categories=["Meat"],
            size="1 lb",
            regular=1.00,
        ),
        _product(
            product_id="stable-brand-choice",
            description="Chicken Breast",
            categories=["Meat"],
            size="1 lb",
            regular=5.99,
        ),
    ]
    products[0]["brand"] = "Brand B"
    products[1]["brand"] = "Brand A"
    responses = [
        FakeResponse(_TOKEN),
        FakeResponse({"data": products}),
        FakeResponse(_TOKEN),
        FakeResponse({"data": products}),
    ]
    calls = _install_responses(monkeypatch, responses)
    client = app.create_app({"TESTING": True}).test_client()

    with using_grocery_pricing_mode("kroger"):
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

    assert v1.status_code == v2.status_code == 200
    v1_recipe = v1.get_json()["recipes"][0]
    v2_recipe = v2.get_json()["recipes"][0]
    assert v1_recipe["estimated_total_cost"] == 5.99
    assert v2_recipe["estimated_total_cost"] == 5.99
    assert v2_recipe["ingredients"][0]["package_purchase"] == {
        "status": "available",
        "source": "kroger",
        "selected_product": "Chicken Breast",
        "product_id": "stable-brand-choice",
        "package_price": 5.99,
        "package_quantity": 1.0,
        "package_unit": "lb",
        "currency": "USD",
        "packages_required": 1,
        "purchase_cost": 5.99,
    }
    assert len(calls) == 4


def test_smoke_test_requires_live_opt_in():
    with pytest.raises(SystemExit):
        smoke_test_kroger._parse_args([])


def test_smoke_test_rejects_nonfinite_quantity():
    with pytest.raises(SystemExit):
        smoke_test_kroger._parse_args(
            ["--live", "--quantity", "nan"]
        )


def test_smoke_test_budget_is_exactly_oauth_plus_one_search():
    assert smoke_test_kroger._MAX_HTTP_REQUESTS == 2
    assert "WITH CAP 2" in smoke_test_kroger._CONFIRMATION


def test_smoke_test_enforces_two_request_budget(monkeypatch, capsys):
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: smoke_test_kroger._CONFIRMATION,
    )

    def fake_pricing(requirements):
        record_external_request()
        record_external_request()
        requirement = requirements[0]
        return {
            (
                requirement["name"].casefold(),
                requirement["quantity"],
                requirement["unit"].casefold(),
            ): GroceryPriceQuote(
                ingredient_use_cost=3.99,
                source="kroger",
                selected_product="Chicken Breast",
                package_price=7.98,
                package_quantity=2.0,
                package_unit="lb",
                currency="USD",
            )
        }

    monkeypatch.setattr(
        smoke_test_kroger,
        "get_ingredient_pricing",
        fake_pricing,
    )

    result = smoke_test_kroger.main(["--live"])
    output = capsys.readouterr().out

    assert result == 0
    assert "external_http_requests=2" in output
