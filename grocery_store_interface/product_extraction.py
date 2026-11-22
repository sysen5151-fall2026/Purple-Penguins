"""Extract and validate product and price fields from parsed HTML cards."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from pricing_timing import measure_stage

from .errors import GroceryPricingError
from .models import ProductCandidate


_PRICE_TEXT = re.compile(
    r"^\s*(?:(?:USD)\s*)?\$?\s*"
    r"(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
    r"\s*$",
    re.IGNORECASE,
)


def extract_product_candidates(
    raw_cards: list[dict[str, str | None]],
) -> list[ProductCandidate]:
    """Convert parser fields into typed candidates without inventing defaults."""
    with measure_stage("product_extraction"):
        candidates: list[ProductCandidate] = []
        for card in raw_cards:
            description = card.get("description")
            if not isinstance(description, str) or not description.strip():
                raise _invalid_product_data("A product name is missing.")

            categories_text = card.get("categories")
            categories = (
                tuple(
                    category.strip()
                    for category in categories_text.split("|")
                    if category.strip()
                )
                if isinstance(categories_text, str)
                else ()
            )
            candidates.append(
                ProductCandidate(
                    description=description.strip(),
                    product_id=_optional_text(card.get("product_id")),
                    item_id=_optional_text(card.get("item_id")) or "",
                    brand=_optional_text(card.get("brand")) or "",
                    categories=categories,
                    price_text=_optional_text(card.get("price")),
                    package_size_text=_optional_text(card.get("package_size")),
                    sold_by=_optional_text(card.get("sold_by")),
                    currency=_optional_text(card.get("currency")),
                )
            )
        return candidates


def extract_price(candidate: ProductCandidate) -> Decimal:
    """Parse an explicit positive USD price from the selected product card."""
    with measure_stage("price_extraction"):
        if candidate.currency != "USD" or candidate.price_text is None:
            raise _invalid_product_data(
                "A product price or USD currency is unavailable."
            )
        match = _PRICE_TEXT.fullmatch(candidate.price_text)
        if match is None:
            raise _invalid_product_data("A product price is malformed.")
        try:
            price = Decimal(match.group("amount").replace(",", ""))
        except InvalidOperation as error:
            raise _invalid_product_data("A product price is malformed.") from error
        if not price.is_finite() or price <= 0:
            raise _invalid_product_data("A product price is not positive and finite.")
        return price


def _optional_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _invalid_product_data(log_message: str) -> GroceryPricingError:
    return GroceryPricingError(
        "A valid grocery price or package listing is unavailable.",
        status_code=502,
        log_message=log_message,
    )
