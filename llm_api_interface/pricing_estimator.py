"""Experimental, isolated LLM pricing estimates for Chapter 10.4 benchmarks."""

from __future__ import annotations

import json
import math
import os
from typing import TypedDict

from openai import APIStatusError, OpenAI, OpenAIError

from .openai_adapter import DEFAULT_MODEL, MAX_OUTPUT_TOKENS, _read_timeout
from .errors import RecipeGenerationServiceError
from pricing_timing import record_external_request


_PRICING_SCHEMA = {
    "type": "object",
    "properties": {
        "prices": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ingredient": {"type": "string"},
                    "estimated_price_usd": {"type": "number"},
                },
                "required": ["ingredient", "estimated_price_usd"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["prices"],
    "additionalProperties": False,
}

_SYSTEM_INSTRUCTIONS = (
    "Estimate an unverified US-dollar grocery price for each requested "
    "ingredient name. Treat each name as one prospective purchase item; no "
    "quantity or package size is supplied. Return exactly one estimate per "
    "requested name, with no extra ingredients or commentary. These are "
    "estimates, not verified store prices."
)


class IngredientPriceEstimate(TypedDict):
    ingredient: str
    estimated_price_usd: float


class PricingBenchmarkError(RuntimeError):
    """A safe, structured error for the isolated pricing experiment."""

    def __init__(
        self,
        failure_code: str,
        *,
        provider_status_code: int | None = None,
    ) -> None:
        super().__init__(failure_code)
        self.failure_code = failure_code
        self.provider_status_code = provider_status_code


def create_pricing_client() -> tuple[OpenAI, str]:
    """Create an OpenAI client using the application's server configuration."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise PricingBenchmarkError("missing_api_key")

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip()
    if not model:
        raise PricingBenchmarkError("empty_openai_model")

    try:
        timeout = _read_timeout()
    except RecipeGenerationServiceError as error:
        raise PricingBenchmarkError("invalid_openai_timeout") from error

    try:
        client = OpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )
    except OpenAIError as error:
        raise PricingBenchmarkError("openai_client_initialization_error") from error

    return client, model


def build_pricing_request(ingredients: list[str]) -> list[dict[str, str]]:
    """Validate benchmark inputs and construct the structured request payload."""
    _validate_ingredient_input(ingredients)
    return [
        {"role": "system", "content": _SYSTEM_INSTRUCTIONS},
        {
            "role": "user",
            "content": json.dumps({"ingredients": ingredients}),
        },
    ]


def request_price_estimates(
    client: OpenAI,
    model: str,
    request_input: list[dict[str, str]],
) -> object:
    """Send one structured pricing request without retrying."""
    try:
        record_external_request()
        response = client.responses.create(
            model=model,
            input=request_input,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "ingredient_price_estimates",
                    "strict": True,
                    "schema": _PRICING_SCHEMA,
                }
            },
        )
    except APIStatusError as error:
        raise PricingBenchmarkError(
            "openai_status_error",
            provider_status_code=error.status_code,
        ) from error
    except OpenAIError as error:
        raise PricingBenchmarkError(
            f"openai_{type(error).__name__}"
        ) from error

    return getattr(response, "output_text", None)


def validate_price_estimates(
    output_text: object,
    ingredients: list[str],
) -> list[IngredientPriceEstimate]:
    """Validate estimate shape, ingredient coverage, and finite USD amounts."""
    expected_names = _validate_ingredient_input(ingredients)
    if not isinstance(output_text, str) or not output_text.strip():
        raise PricingBenchmarkError("empty_pricing_response")

    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise PricingBenchmarkError("malformed_pricing_json") from error

    if not isinstance(payload, dict) or set(payload) != {"prices"}:
        raise PricingBenchmarkError("invalid_pricing_response_shape")

    raw_prices = payload["prices"]
    if not isinstance(raw_prices, list) or len(raw_prices) != len(ingredients):
        raise PricingBenchmarkError("invalid_pricing_response_count")

    expected_by_normalized = {
        _normalize_name(ingredient): ingredient for ingredient in expected_names
    }
    seen: set[str] = set()
    validated: list[IngredientPriceEstimate] = []
    for item in raw_prices:
        if (
            not isinstance(item, dict)
            or set(item) != {"ingredient", "estimated_price_usd"}
        ):
            raise PricingBenchmarkError("invalid_pricing_item_shape")

        ingredient = item["ingredient"]
        amount = item["estimated_price_usd"]
        if not isinstance(ingredient, str) or not ingredient.strip():
            raise PricingBenchmarkError("invalid_pricing_ingredient")

        normalized_name = _normalize_name(ingredient)
        if normalized_name not in expected_by_normalized or normalized_name in seen:
            raise PricingBenchmarkError("unexpected_or_duplicate_ingredient")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise PricingBenchmarkError("invalid_estimated_price")

        try:
            price = float(amount)
        except OverflowError as error:
            raise PricingBenchmarkError("invalid_estimated_price") from error
        if not math.isfinite(price) or price < 0:
            raise PricingBenchmarkError("invalid_estimated_price")

        seen.add(normalized_name)
        validated.append(
            {
                "ingredient": expected_by_normalized[normalized_name],
                "estimated_price_usd": price,
            }
        )

    if seen != set(expected_by_normalized):
        raise PricingBenchmarkError("missing_pricing_ingredient")
    return validated


def _validate_ingredient_input(ingredients: list[str]) -> list[str]:
    if not isinstance(ingredients, list) or not ingredients:
        raise PricingBenchmarkError("invalid_ingredient_input")
    if any(not isinstance(ingredient, str) or not ingredient.strip()
           for ingredient in ingredients):
        raise PricingBenchmarkError("invalid_ingredient_input")

    normalized = [_normalize_name(ingredient) for ingredient in ingredients]
    if len(set(normalized)) != len(normalized):
        raise PricingBenchmarkError("duplicate_ingredient_input")
    return [ingredient.strip() for ingredient in ingredients]


def _normalize_name(ingredient: str) -> str:
    return ingredient.strip().casefold()
