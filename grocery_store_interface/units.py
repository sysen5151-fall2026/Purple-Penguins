"""Conservative conversions for recipe quantities and package sizes."""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_CEILING


_UNIT_FACTORS: dict[str, tuple[str, Decimal]] = {
    "mg": ("mass", Decimal("0.001")),
    "g": ("mass", Decimal("1")),
    "gram": ("mass", Decimal("1")),
    "grams": ("mass", Decimal("1")),
    "kg": ("mass", Decimal("1000")),
    "kilogram": ("mass", Decimal("1000")),
    "kilograms": ("mass", Decimal("1000")),
    "oz": ("mass", Decimal("28.349523125")),
    "ounce": ("mass", Decimal("28.349523125")),
    "ounces": ("mass", Decimal("28.349523125")),
    "lb": ("mass", Decimal("453.59237")),
    "lbs": ("mass", Decimal("453.59237")),
    "pound": ("mass", Decimal("453.59237")),
    "pounds": ("mass", Decimal("453.59237")),
    "ml": ("volume", Decimal("1")),
    "milliliter": ("volume", Decimal("1")),
    "milliliters": ("volume", Decimal("1")),
    "l": ("volume", Decimal("1000")),
    "liter": ("volume", Decimal("1000")),
    "liters": ("volume", Decimal("1000")),
    "fl_oz": ("volume", Decimal("29.5735295625")),
    "floz": ("volume", Decimal("29.5735295625")),
    "tsp": ("volume", Decimal("4.92892159375")),
    "teaspoon": ("volume", Decimal("4.92892159375")),
    "teaspoons": ("volume", Decimal("4.92892159375")),
    "tbsp": ("volume", Decimal("14.78676478125")),
    "tablespoon": ("volume", Decimal("14.78676478125")),
    "tablespoons": ("volume", Decimal("14.78676478125")),
    "cup": ("volume", Decimal("236.5882365")),
    "cups": ("volume", Decimal("236.5882365")),
    "pt": ("volume", Decimal("473.176473")),
    "pint": ("volume", Decimal("473.176473")),
    "pints": ("volume", Decimal("473.176473")),
    "qt": ("volume", Decimal("946.352946")),
    "quart": ("volume", Decimal("946.352946")),
    "quarts": ("volume", Decimal("946.352946")),
    "gal": ("volume", Decimal("3785.411784")),
    "gallon": ("volume", Decimal("3785.411784")),
    "gallons": ("volume", Decimal("3785.411784")),
    "count": ("count", Decimal("1")),
    "ct": ("count", Decimal("1")),
    "each": ("count", Decimal("1")),
    "ea": ("count", Decimal("1")),
    "unit": ("count", Decimal("1")),
    "head": ("count", Decimal("1")),
    "bulb": ("count", Decimal("1")),
}
_PACKAGE_SIZE = re.compile(
    r"^\s*(?P<quantity>\d+(?:\.\d+)?|\d+\s*/\s*\d+)\s*"
    r"(?P<unit>[a-zA-Z_]+(?:\s+[a-zA-Z_]+)?)\s*$"
)


def unit_dimension_and_factor(unit: str) -> tuple[str, Decimal]:
    normalized = unit.strip().casefold().replace(".", "").replace(" ", "_")
    try:
        return _UNIT_FACTORS[normalized]
    except KeyError as error:
        raise ValueError("Unsupported ingredient unit.") from error


def parse_package_size(size: object) -> tuple[Decimal, str]:
    if not isinstance(size, str):
        raise ValueError("Package size is missing.")
    if size.strip().casefold() in {"each", "ea", "unit"}:
        return Decimal("1"), "count"

    match = _PACKAGE_SIZE.fullmatch(size)
    if match is None:
        raise ValueError("Package size is not a supported quantity.")

    quantity_text = match.group("quantity")
    if "/" in quantity_text:
        numerator, denominator = quantity_text.split("/", maxsplit=1)
        quantity = Decimal(numerator.strip()) / Decimal(denominator.strip())
    else:
        quantity = Decimal(quantity_text)
    unit = match.group("unit").strip().casefold().replace(".", "")
    if not quantity.is_finite() or quantity <= 0:
        raise ValueError("Package size is not positive and finite.")
    if unit == "fl oz":
        unit = "fl_oz"
    unit_dimension_and_factor(unit)
    return quantity, unit


def normalized_price(
    package_price: Decimal,
    package_quantity: Decimal,
    package_unit: str,
    required_quantity: float,
    required_unit: str,
) -> Decimal:
    package_dimension, package_factor = unit_dimension_and_factor(package_unit)
    required_dimension, required_factor = unit_dimension_and_factor(required_unit)
    if package_dimension != required_dimension:
        raise ValueError("Package and recipe units are not convertible.")

    required = Decimal(str(required_quantity))
    if not required.is_finite() or required <= 0:
        raise ValueError("Recipe quantity is not positive and finite.")

    package_base_quantity = package_quantity * package_factor
    required_base_quantity = required * required_factor
    return package_price * required_base_quantity / package_base_quantity


def whole_packages_required(
    required_quantity: float,
    required_unit: str,
    package_quantity: float,
    package_unit: str,
) -> int:
    package_dimension, package_factor = unit_dimension_and_factor(package_unit)
    required_dimension, required_factor = unit_dimension_and_factor(required_unit)
    if package_dimension != required_dimension:
        raise ValueError("Package and recipe units are not convertible.")

    required = Decimal(str(required_quantity))
    package = Decimal(str(package_quantity))
    if (
        not required.is_finite()
        or required <= 0
        or not package.is_finite()
        or package <= 0
    ):
        raise ValueError("Package and recipe quantities must be positive.")

    required_base_quantity = required * required_factor
    package_base_quantity = package * package_factor
    count = (required_base_quantity / package_base_quantity).to_integral_value(
        rounding=ROUND_CEILING
    )
    return int(count)


SUPPORTED_RECIPE_UNITS = (
    "g",
    "kg",
    "oz",
    "lb",
    "ml",
    "l",
    "fl_oz",
    "tsp",
    "tbsp",
    "cup",
    "count",
    "head",
    "bulb",
)
