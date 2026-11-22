"""Grocery pricing boundary with fixture, stub, and disabled live modes."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterator

from pricing_timing import measure_stage

from .errors import GroceryPricingError
from .html_parser import parse_product_listing_html
from .models import (
    GroceryPriceQuote,
    IngredientRequirement,
    IngredientRequirementKey,
    ProductCandidate,
    requirement_key,
)
from .product_extraction import extract_product_candidates
from .product_matching import select_product_offer
from .retrieval import FixturePageRetriever, HtmlPageRetriever

MAX_INGREDIENT_LOOKUPS_PER_REQUEST = 25

# These are explicit deterministic demo values, not retailer prices.
_STUB_PRICING = {
    "pasta": 1.99,
    "eggs": 3.49,
    "bacon": 5.99,
    "broccoli": 2.49,
    "bell peppers": 1.99,
    "onions": 0.99,
    "soy sauce": 2.99,
}

_MODE_OVERRIDE: ContextVar[str | None] = ContextVar(
    "grocery_pricing_mode_override",
    default=None,
)


def get_grocery_pricing_mode() -> str:
    """Return the configured source; local HTML fixtures are the safe default."""
    override = _MODE_OVERRIDE.get()
    if override is not None:
        return override
    return os.getenv("GROCERY_PRICING_MODE", "html_fixture").strip().casefold()


@contextmanager
def using_grocery_pricing_mode(mode: str) -> Iterator[None]:
    token = _MODE_OVERRIDE.set(mode.strip().casefold())
    try:
        yield
    finally:
        _MODE_OVERRIDE.reset(token)


def get_ingredient_pricing(
    ingredients: list[IngredientRequirement],
    *,
    page_retriever: HtmlPageRetriever | None = None,
) -> dict[IngredientRequirementKey, GroceryPriceQuote]:
    """Return recipe-use quotes from local HTML fixtures or the offline stub."""
    mode = get_grocery_pricing_mode()
    if mode == "stub":
        pricing: dict[IngredientRequirementKey, GroceryPriceQuote] = {}
        with measure_stage("in_memory_lookup"):
            for requirement in ingredients:
                pricing[requirement_key(requirement)] = GroceryPriceQuote(
                    ingredient_use_cost=_STUB_PRICING.get(
                        requirement["name"],
                        1.00,
                    ),
                    source="stub",
                )
        return pricing

    if mode == "kroger":
        return _get_kroger_pricing(ingredients)

    if mode == "html_live":
        raise GroceryPricingError(
            "Live grocery webpage pricing is disabled until an authorized "
            "source is approved and configured.",
            status_code=503,
            log_message="Live HTML pricing has no approved source configured.",
        )
    if mode != "html_fixture":
        raise GroceryPricingError(
            "Grocery pricing is not configured. Please contact the "
            "application administrator.",
            status_code=503,
            log_message=(
                "GROCERY_PRICING_MODE must be 'html_fixture', 'html_live', "
                    "'kroger', or 'stub'."
            ),
        )

    unique_names = {
        requirement["name"].strip().casefold()
        for requirement in ingredients
    }
    if len(unique_names) > MAX_INGREDIENT_LOOKUPS_PER_REQUEST:
        raise GroceryPricingError(
            "This recipe request contains too many distinct ingredients for "
            "coursework fixture pricing.",
            status_code=503,
            log_message=(
                "HTML fixture lookup limit exceeded "
                f"({len(unique_names)} unique ingredients)."
            ),
        )

    retriever = page_retriever or FixturePageRetriever()
    product_candidates: dict[str, list[ProductCandidate]] = {}
    pricing: dict[IngredientRequirementKey, GroceryPriceQuote] = {}
    for requirement in ingredients:
        normalized_name = requirement["name"].strip().casefold()
        if normalized_name not in product_candidates:
            page = retriever.retrieve_page(requirement["name"])
            with measure_stage("html_parsing"):
                raw_cards = parse_product_listing_html(page)
            product_candidates[normalized_name] = extract_product_candidates(
                raw_cards
            )

        offer = select_product_offer(
            product_candidates[normalized_name],
            requirement["name"],
            requirement["quantity"],
            requirement["unit"],
            source="html_fixture",
        )
        pricing[requirement_key(requirement)] = GroceryPriceQuote(
            ingredient_use_cost=float(offer.normalized_use_cost),
            source="html_fixture",
            selected_product=offer.candidate.description,
            product_id=offer.candidate.product_id,
            package_price=float(_round_to_cents(offer.price_usd)),
            package_quantity=float(offer.package_quantity),
            package_unit=offer.package_unit,
            currency="USD",
        )
    return pricing


def _get_kroger_pricing(
    ingredients: list[IngredientRequirement],
) -> dict[IngredientRequirementKey, GroceryPriceQuote]:
    unique_names = {
        requirement["name"].strip().casefold()
        for requirement in ingredients
    }
    if len(unique_names) > MAX_INGREDIENT_LOOKUPS_PER_REQUEST:
        raise GroceryPricingError(
            "This recipe request contains too many distinct ingredients for "
            "live grocery pricing.",
            status_code=503,
            log_message=(
                "Kroger lookup limit exceeded "
                f"({len(unique_names)} unique ingredient names)."
            ),
        )

    from .kroger_api import KrogerProductClient

    client = KrogerProductClient.from_environment()
    candidates_by_name: dict[str, list[ProductCandidate]] = {}
    pricing: dict[IngredientRequirementKey, GroceryPriceQuote] = {}
    for requirement in ingredients:
        normalized_name = requirement["name"].strip().casefold()
        if normalized_name not in candidates_by_name:
            with measure_stage("grocery_product_search"):
                candidates_by_name[normalized_name] = client.search_products(
                    requirement["name"]
                )
        offer = select_product_offer(
            candidates_by_name[normalized_name],
            requirement["name"],
            requirement["quantity"],
            requirement["unit"],
            source="kroger",
        )
        pricing[requirement_key(requirement)] = GroceryPriceQuote(
            ingredient_use_cost=float(offer.normalized_use_cost),
            source="kroger",
            selected_product=offer.candidate.description,
            product_id=offer.candidate.product_id,
            package_price=float(_round_to_cents(offer.price_usd)),
            package_quantity=float(offer.package_quantity),
            package_unit=offer.package_unit,
            currency=offer.candidate.currency,
        )
    return pricing


def _round_to_cents(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
