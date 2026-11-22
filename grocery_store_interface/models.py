"""Internal grocery-pricing data structures."""

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict


class IngredientRequirement(TypedDict):
    name: str
    quantity: float
    unit: str


IngredientRequirementKey = tuple[str, float, str]


@dataclass(frozen=True)
class GroceryPriceQuote:
    ingredient_use_cost: float
    source: str
    selected_product: str | None = None
    product_id: str | None = None
    package_price: float | None = None
    package_quantity: float | None = None
    package_unit: str | None = None
    currency: str | None = None


@dataclass(frozen=True)
class ProductCandidate:
    description: str
    product_id: str | None
    item_id: str
    brand: str
    categories: tuple[str, ...]
    price_text: str | None
    package_size_text: str | None
    sold_by: str | None
    currency: str | None


@dataclass(frozen=True)
class ProductOffer:
    candidate: ProductCandidate
    price_usd: Decimal
    package_quantity: Decimal
    package_unit: str
    normalized_use_cost: Decimal


def requirement_key(requirement: IngredientRequirement) -> IngredientRequirementKey:
    return (
        requirement["name"].strip().casefold(),
        float(requirement["quantity"]),
        requirement["unit"].strip().casefold(),
    )
