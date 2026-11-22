"""Conservative ingredient matching and package-price normalization."""

from __future__ import annotations

import logging
import re
from decimal import Decimal, ROUND_HALF_UP

from pricing_timing import measure_stage

from .errors import GroceryPricingError
from .models import ProductCandidate, ProductOffer
from .product_extraction import extract_price
from .units import (
    normalized_price,
    parse_package_size,
    unit_dimension_and_factor,
    whole_packages_required,
)


_WORDS = re.compile(r"[a-z0-9]+")
_LOGGER = logging.getLogger(__name__)
_PREPARED_PRODUCT_TERMS = {
    "bar",
    "bars",
    "broth",
    "candy",
    "cereal",
    "chocolate",
    "cracker",
    "crackers",
    "deli",
    "dessert",
    "desserts",
    "drink",
    "flavored",
    "flavor",
    "flavour",
    "marinade",
    "meal",
    "mix",
    "nugget",
    "nuggets",
    "patty",
    "patties",
    "pudding",
    "ramen",
    "sandwich",
    "seasoned",
    "seasoning",
    "salad",
    "sauce",
    "snack",
    "soup",
    "stock",
    "pasta",
    "powder",
    "prepared",
    "bakery",
    "dinner",
    "dinners",
    "lunch",
    "lunches",
    "breaded",
    "breading",
    "strips",
    "casserole",
    "entree",
    "beverage",
    "syrup",
    "yogurt",
    "filled",
    "stuffed",
    "ravioli",
    "tortellini",
    "crumb",
    "crumbs",
    "breadcrumb",
    "breadcrumbs",
    "crouton",
    "croutons",
    "stuffing",
    "breading",
}
_PRODUCT_TYPE_TERMS = {
    "bread",
    "cheese",
    "chicken",
    "egg",
    "eggs",
    "fish",
    "milk",
    "pasta",
    "rice",
    "squash",
    "butter",
    "cream",
}
_CONTROLLED_INGREDIENT_ALIASES = {
    "pasta": {
        "farfalle",
        "fettuccine",
        "fusilli",
        "linguine",
        "macaroni",
        "penne",
        "rigatoni",
        "rotini",
        "spaghetti",
        "ziti",
    },
}
_SPECIALTY_TERMS = {
    "organic",
    "premium",
    "artisan",
    "artisanal",
    "gourmet",
    "imported",
    "specialty",
    "flavored",
    "flavoured",
    "gluten",
    "vegan",
    "keto",
    "protein",
    "almond",
    "oat",
    "soy",
    "coconut",
    "fresh",
    "frozen",
}
_PACKAGE_COUNT_PREFERENCE_LIMIT = 2


def select_product_offer(
    candidates: list[ProductCandidate],
    ingredient_name: str,
    required_quantity: float,
    required_unit: str,
    *,
    source: str = "unknown",
) -> ProductOffer:
    """Choose a comparable, priceable representative without price ranking."""
    with measure_stage("product_matching"):
        return _select_product_offer(
            candidates,
            ingredient_name,
            required_quantity,
            required_unit,
            source=source,
        )


def _select_product_offer(
    candidates: list[ProductCandidate],
    ingredient_name: str,
    required_quantity: float,
    required_unit: str,
    *,
    source: str,
) -> ProductOffer:
    candidate_count = len(candidates)
    matching = [
        candidate
        for candidate in candidates
        if _is_relevant_candidate(candidate, ingredient_name)
    ]
    relevance_count = len(matching)
    if not candidates:
        raise _matching_failure(
            source,
            ingredient_name,
            candidate_count,
            relevance_count,
            0,
            failure_category="no_candidates",
            public_message=(
                "A grocery product could not be matched reliably to an "
                "ingredient."
            ),
        )
    if not matching:
        raise _matching_failure(
            source,
            ingredient_name,
            candidate_count,
            relevance_count,
            0,
            failure_category="no_confident_match",
            public_message=(
                "A grocery product could not be matched reliably to an "
                "ingredient."
            ),
        )

    offers: list[ProductOffer] = []
    invalid_package = False
    invalid_price = False
    unit_mismatch = False
    compatible_packages = 0
    validation_counts = {
        "missing_sold_by_count": 0,
        "non_unit_sold_by_count": 0,
        "missing_package_size_count": 0,
        "unsupported_package_size_count": 0,
        "incompatible_units_count": 0,
        "invalid_price_count": 0,
    }
    for candidate in matching:
        if not isinstance(candidate.sold_by, str) or not candidate.sold_by.strip():
            validation_counts["missing_sold_by_count"] += 1
            invalid_package = True
            continue
        if candidate.sold_by.casefold() != "unit":
            validation_counts["non_unit_sold_by_count"] += 1
            invalid_package = True
            continue

        if (
            not isinstance(candidate.package_size_text, str)
            or not candidate.package_size_text.strip()
        ):
            validation_counts["missing_package_size_count"] += 1
            invalid_package = True
            continue
        try:
            with measure_stage("unit_package_normalization"):
                package_quantity, package_unit = parse_package_size(
                    candidate.package_size_text
                )
        except ValueError:
            validation_counts["unsupported_package_size_count"] += 1
            invalid_package = True
            continue

        try:
            with measure_stage("unit_package_normalization"):
                package_dimension, _ = unit_dimension_and_factor(package_unit)
                required_dimension, _ = unit_dimension_and_factor(required_unit)
                if package_dimension != required_dimension:
                    raise ValueError("Package and recipe units are incompatible.")
        except ValueError:
            validation_counts["incompatible_units_count"] += 1
            unit_mismatch = True
            continue

        compatible_packages += 1
        try:
            price = extract_price(candidate)
            with measure_stage("unit_package_normalization"):
                use_cost = normalized_price(
                    price,
                    package_quantity,
                    package_unit,
                    required_quantity,
                    required_unit,
                )
        except GroceryPricingError:
            validation_counts["invalid_price_count"] += 1
            invalid_price = True
            continue
        except (ArithmeticError, OverflowError, ValueError):
            validation_counts["incompatible_units_count"] += 1
            unit_mismatch = True
            continue

        offers.append(
            ProductOffer(
                candidate=candidate,
                price_usd=price,
                package_quantity=package_quantity,
                package_unit=package_unit,
                normalized_use_cost=_round_to_cents(use_cost),
            )
        )

    if not offers:
        failure_category = "invalid_package"
        if compatible_packages and invalid_price:
            failure_category = "invalid_price"
            public_message = (
                "A product price or package quantity is missing or invalid."
            )
        elif unit_mismatch and not invalid_package:
            failure_category = "incompatible_units"
            public_message = (
                "A product matched, but its package unit is incompatible with "
                "the recipe quantity."
            )
        elif invalid_package:
            public_message = (
                "A product price or package quantity is missing or invalid."
            )
        elif invalid_price:
            failure_category = "invalid_price"
            public_message = (
                "A product price or package quantity is missing or invalid."
            )
        else:
            public_message = "A product package is unavailable or invalid."
        raise _matching_failure(
            source,
            ingredient_name,
            candidate_count,
            relevance_count,
            0,
            failure_category=failure_category,
            public_message=public_message,
            validation_counts=validation_counts,
        )

    eligible_priceable_count = len(offers)
    preferred_specialty_score = min(
        _specialty_score(offer.candidate, ingredient_name)
        for offer in offers
    )
    standard_or_preferred_offers = [
        offer
        for offer in offers
        if _specialty_score(offer.candidate, ingredient_name)
        == preferred_specialty_score
    ]

    offers_by_identity: dict[str, list[ProductOffer]] = {}
    for offer in standard_or_preferred_offers:
        offers_by_identity.setdefault(
            _product_identity(offer.candidate),
            [],
        ).append(offer)

    representative_offers: list[ProductOffer] = []
    comparison_keys: set[tuple[str, str]] = set()
    for identity_offers in offers_by_identity.values():
        identity_keys = {
            _product_comparability_key(
                offer.candidate,
                ingredient_name,
            )
            for offer in identity_offers
        }
        if len(identity_keys) > 1:
            raise _matching_failure(
                source,
                ingredient_name,
                candidate_count,
                relevance_count,
                eligible_priceable_count,
                failure_category="ambiguous_match",
                public_message=(
                    "More than one materially different product matches an "
                    "ingredient. Pricing is unavailable until the match is "
                    "clarified."
                ),
                validation_counts=validation_counts,
            )
        comparison_keys.update(identity_keys)
        representative_offers.append(
            min(
                identity_offers,
                key=lambda offer: _selection_key(
                    offer,
                    required_quantity,
                    required_unit,
                    ingredient_name,
                ),
            )
        )

    if len(comparison_keys) > 1:
        raise _matching_failure(
            source,
            ingredient_name,
            candidate_count,
            relevance_count,
            eligible_priceable_count,
            failure_category="ambiguous_match",
            public_message=(
                "More than one materially different product matches an "
                "ingredient. Pricing is unavailable until the match is "
                "clarified."
            ),
            validation_counts=validation_counts,
        )

    selected = min(
        representative_offers,
        key=lambda offer: _selection_key(
            offer,
            required_quantity,
            required_unit,
            ingredient_name,
        ),
    )
    selection_reason = _selection_reason(
        offers,
        selected,
        required_quantity,
        required_unit,
        ingredient_name,
    )
    _LOGGER.info(
        "Product match selected source=%s requested_ingredient=%r "
        "candidate_count=%d relevance_count=%d "
        "eligible_priceable_count=%d selected_product_id=%r "
        "selection_policy_reason=%s",
        source,
        _safe_ingredient_label(ingredient_name),
        candidate_count,
        relevance_count,
        eligible_priceable_count,
        selected.candidate.product_id,
        selection_reason,
    )
    return selected


def _is_relevant_candidate(
    candidate: ProductCandidate,
    ingredient_name: str,
) -> bool:
    if not candidate.description.strip():
        return False

    query_tokens = _WORDS.findall(ingredient_name.casefold())
    description_tokens = _WORDS.findall(candidate.description.casefold())
    if not query_tokens:
        return False

    query_token_set = set(query_tokens)
    description_match = _contains_phrase(description_tokens, query_tokens)
    query_key = " ".join(query_tokens)
    aliases = _CONTROLLED_INGREDIENT_ALIASES.get(query_key, set())
    alias_tokens = {
        tuple(_WORDS.findall(alias))
        for alias in aliases
    }
    alias_match = any(
        _contains_phrase(description_tokens, list(alias))
        for alias in alias_tokens
    )
    category_tokens_by_category = [
        _WORDS.findall(category.casefold())
        for category in candidate.categories
    ]
    category_match = any(
        _contains_phrase(category_tokens, query_tokens)
        for category_tokens in category_tokens_by_category
    )

    all_product_tokens = set(description_tokens)
    for category_tokens in category_tokens_by_category:
        all_product_tokens.update(category_tokens)
    additional_tokens = all_product_tokens - query_token_set
    if additional_tokens.intersection(_PREPARED_PRODUCT_TERMS):
        return False

    if len(query_tokens) > 1 and not description_match:
        return False
    if not description_match and not alias_match and not category_match:
        return False

    if not description_match:
        description_types = set(description_tokens).intersection(
            _PRODUCT_TYPE_TERMS
        )
        allowed_types = query_token_set.union(
            token
            for alias in alias_tokens
            for token in alias
        )
        if description_types - allowed_types:
            return False
    return True


def _contains_phrase(tokens: list[str], phrase: list[str]) -> bool:
    width = len(phrase)
    return any(
        tokens[index:index + width] == phrase
        for index in range(len(tokens) - width + 1)
    )


def _product_identity(candidate: ProductCandidate) -> str:
    if candidate.product_id:
        return candidate.product_id.casefold()
    description = " ".join(_WORDS.findall(candidate.description.casefold()))
    return f"{candidate.brand.casefold()}:{description}"


def _product_comparability_key(
    candidate: ProductCandidate,
    ingredient_name: str,
) -> tuple[str, str]:
    query_tokens = _WORDS.findall(ingredient_name.casefold())
    query = " ".join(query_tokens)
    family = "pasta" if query.endswith(" pasta") or query == "pasta" else query
    candidate_tokens = set(_WORDS.findall(candidate.description.casefold()))
    category_tokens = {
        token
        for category in candidate.categories
        for token in _WORDS.findall(category.casefold())
    }
    all_tokens = candidate_tokens | category_tokens

    if len(query_tokens) > 1:
        return family, query
    if family == "pasta":
        if all_tokens.intersection({"fresh", "filled", "stuffed"}):
            return family, "fresh_or_filled"
        return family, "standard_pasta"
    if family == "milk":
        if all_tokens.intersection({"almond", "oat", "soy", "coconut", "plant"}):
            return family, "plant_based"
        if all_tokens.intersection({"powder", "powdered", "condensed", "evaporated"}):
            return family, "concentrated_or_powdered"
        return family, "fluid"
    if family in {"egg", "eggs"}:
        if all_tokens.intersection({"liquid", "powder", "substitute"}):
            return family, "liquid_or_substitute"
        return "eggs", "shell"
    if family == "chicken":
        forms = (
            ({"breast"}, "breast"),
            ({"thigh", "thighs"}, "thigh"),
            ({"drumstick", "drumsticks"}, "drumstick"),
            ({"wing", "wings"}, "wing"),
            ({"ground"}, "ground"),
            ({"whole", "roaster", "fryer"}, "whole"),
            ({"stock", "broth"}, "stock_or_broth"),
        )
        for tokens, form in forms:
            if all_tokens.intersection(tokens):
                return family, form
    return family, "standard"


def _specialty_score(
    candidate: ProductCandidate,
    ingredient_name: str,
) -> int:
    query_tokens = _WORDS.findall(ingredient_name.casefold())
    query_set = set(query_tokens)
    candidate_tokens = (
        set(_WORDS.findall(candidate.description.casefold()))
        | set(_WORDS.findall(candidate.brand.casefold()))
        | {
            token
            for category in candidate.categories
            for token in _WORDS.findall(category.casefold())
        }
    )
    return len(
        (candidate_tokens - query_set).intersection(_SPECIALTY_TERMS)
    )


def _selection_key(
    offer: ProductOffer,
    required_quantity: float,
    required_unit: str,
    ingredient_name: str,
) -> tuple[object, ...]:
    return (
        *_selection_non_price_key(
            offer,
            required_quantity,
            required_unit,
            ingredient_name,
        ),
        offer.price_usd,
    )


def _selection_non_price_key(
    offer: ProductOffer,
    required_quantity: float,
    required_unit: str,
    ingredient_name: str,
) -> tuple[object, ...]:
    package_fit = _package_fit_key(
        offer,
        required_quantity,
        required_unit,
    )
    return (
        _specialty_score(offer.candidate, ingredient_name),
        *package_fit,
        " ".join(_WORDS.findall(offer.candidate.description.casefold())),
        offer.candidate.brand.casefold(),
        (offer.candidate.product_id or "").casefold(),
        offer.candidate.item_id.casefold(),
    )


def _package_fit_key(
    offer: ProductOffer,
    required_quantity: float,
    required_unit: str,
) -> tuple[int, Decimal, int]:
    package_dimension, package_factor = unit_dimension_and_factor(
        offer.package_unit
    )
    required_dimension, required_factor = unit_dimension_and_factor(
        required_unit
    )
    if package_dimension != required_dimension:
        raise ValueError("Package and recipe units are not convertible.")

    required_base = Decimal(str(required_quantity)) * required_factor
    package_base = offer.package_quantity * package_factor
    package_count = whole_packages_required(
        required_quantity,
        required_unit,
        float(offer.package_quantity),
        offer.package_unit,
    )
    excess_ratio = (
        package_base * package_count - required_base
    ) / required_base
    package_count_bucket = (
        0
        if package_count <= _PACKAGE_COUNT_PREFERENCE_LIMIT
        and excess_ratio <= 1
        else 1
    )
    return (
        package_count_bucket,
        Decimal(package_count) + excess_ratio,
        package_count,
    )


def _selection_reason(
    offers: list[ProductOffer],
    selected: ProductOffer,
    required_quantity: float,
    required_unit: str,
    ingredient_name: str,
) -> str:
    if len(offers) == 1:
        return "only_eligible_candidate"
    selected_specialty_score = _specialty_score(
        selected.candidate,
        ingredient_name,
    )
    if any(
        _specialty_score(offer.candidate, ingredient_name)
        > selected_specialty_score
        for offer in offers
    ):
        return "preferred_standard_variant"
    selected_fit = _package_fit_key(
        selected,
        required_quantity,
        required_unit,
    )
    if any(
        _package_fit_key(offer, required_quantity, required_unit)
        != selected_fit
        for offer in offers
    ):
        return "package_fit"
    selected_non_price_key = _selection_non_price_key(
        selected,
        required_quantity,
        required_unit,
        ingredient_name,
    )
    if any(
        _selection_non_price_key(
            offer,
            required_quantity,
            required_unit,
            ingredient_name,
        )
        == selected_non_price_key
        and offer.price_usd != selected.price_usd
        for offer in offers
    ):
        return "final_price_tiebreak_for_duplicate_offer"
    return "stable_non_price_tiebreak"


def _safe_ingredient_label(ingredient_name: str) -> str:
    collapsed = " ".join(ingredient_name.split())
    printable = "".join(
        character for character in collapsed if character.isprintable()
    )
    return printable[:80] or "<blank>"


def _matching_failure(
    source: str,
    ingredient_name: str,
    candidate_count: int,
    relevance_count: int,
    eligible_priceable_count: int,
    *,
    failure_category: str,
    public_message: str,
    validation_counts: dict[str, int] | None = None,
) -> GroceryPricingError:
    validation_details = " ".join(
        f"{name}={count}"
        for name, count in (validation_counts or {}).items()
    )
    validation_suffix = (
        f" {validation_details}" if validation_details else ""
    )
    return GroceryPricingError(
        public_message,
        status_code=503,
        log_message=(
            "Product matching failure "
            f"source={source} "
            f"failure_category={failure_category} "
            f"requested_ingredient={_safe_ingredient_label(ingredient_name)!r} "
            f"candidate_count={candidate_count} "
            f"relevance_count={relevance_count} "
            f"eligible_priceable_count={eligible_priceable_count}"
            f"{validation_suffix}"
        ),
    )
def _package_purchase_cost_cents(
    offer: ProductOffer,
    required_quantity: float,
    required_unit: str,
) -> int:
    packages = whole_packages_required(
        required_quantity,
        required_unit,
        float(offer.package_quantity),
        offer.package_unit,
    )
    return int(_round_to_cents(offer.price_usd) * 100) * packages


def _round_to_cents(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
