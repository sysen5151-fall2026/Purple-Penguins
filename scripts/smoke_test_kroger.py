"""Explicitly opt-in, single-ingredient Kroger API integration smoke test."""

from __future__ import annotations

import argparse
import math

from grocery_store_interface import (
    GroceryPricingError,
    get_ingredient_pricing,
    using_grocery_pricing_mode,
)
from grocery_store_interface.units import unit_dimension_and_factor
from pricing_timing import (
    ExternalRequestBudget,
    ExternalRequestBudgetExceeded,
    PricingMeasurement,
    activate_measurement,
    activate_request_budget,
)


_MAX_HTTP_REQUESTS = 2
_CONFIRMATION = "RUN ONE KROGER SMOKE TEST WITH CAP 2"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one explicitly authorized, single-ingredient Kroger pricing "
            "smoke test."
        )
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly opt into one OAuth request and one product search.",
    )
    parser.add_argument("--ingredient", default="chicken breast")
    parser.add_argument("--quantity", type=float, default=16.0)
    parser.add_argument("--unit", default="oz")
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("Pass --live to enable the one controlled API smoke test.")
    if not math.isfinite(args.quantity) or args.quantity <= 0:
        parser.error("--quantity must be positive and finite.")
    if not args.ingredient.strip():
        parser.error("--ingredient must not be blank.")
    if not args.unit.strip():
        parser.error("--unit must not be blank.")
    try:
        unit_dimension_and_factor(args.unit)
    except ValueError:
        parser.error("--unit must be a supported recipe unit.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    confirmation = input(
        f"Type '{_CONFIRMATION}' to continue: "
    ).strip()
    if confirmation != _CONFIRMATION:
        print("Kroger smoke test cancelled; no request was sent.")
        return 2

    measurement = PricingMeasurement(
        scenario="actual_kroger_api_smoke_test",
        mode="kroger",
        input_dataset_id="single-ingredient-kroger-smoke-v1",
    )
    request_budget = ExternalRequestBudget(_MAX_HTTP_REQUESTS)
    try:
        with (
            using_grocery_pricing_mode("kroger"),
            activate_measurement(measurement),
            activate_request_budget(request_budget),
        ):
            quote = get_ingredient_pricing(
                [
                    {
                        "name": args.ingredient.strip(),
                        "quantity": args.quantity,
                        "unit": args.unit.strip(),
                    }
                ]
            )[
                (
                    args.ingredient.strip().casefold(),
                    float(args.quantity),
                    args.unit.strip().casefold(),
                )
            ]
        measurement.mark_success()
    except (
        ExternalRequestBudgetExceeded,
        GroceryPricingError,
    ) as error:
        measurement.mark_failure(
            error,
            provider_status_code=getattr(error, "provider_status_code", None),
        )
        print(f"Smoke test failed: {getattr(error, 'public_message', str(error))}")
        print(f"external_http_requests={measurement.provider_request_count}")
        return 1

    print(
        "Kroger smoke test succeeded: "
        f"product={quote.selected_product}; "
        f"ingredient_use_cost_usd={quote.ingredient_use_cost:.2f}; "
        f"package_price_usd={quote.package_price}; "
        f"package_quantity={quote.package_quantity} {quote.package_unit}"
    )
    print(f"external_http_requests={measurement.provider_request_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
