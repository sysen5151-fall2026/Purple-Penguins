"""OpenAI recipe generation adapter for F.2.4.4 and the C.3 LLM API."""

import json
import math
import os
import time
from typing import TypedDict

from openai import (
    APIConnectionError,
    APIStatusError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from .errors import RecipeGenerationServiceError

MAX_TOTAL_ATTEMPTS = 10
DEFAULT_MODEL = "gpt-6-luna"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_TIMEOUT_SECONDS = 120.0
MAX_OUTPUT_TOKENS = 2048
MAX_RECIPES = 5
MAX_INGREDIENTS_PER_RECIPE = 40

_RECIPE_SCHEMA = {
    "type": "object",
    "properties": {
        "recipes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "ingredients"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["recipes"],
    "additionalProperties": False,
}

_SYSTEM_INSTRUCTIONS = (
    "Generate practical recipe ideas using the user's preferences. "
    "Take dietary restrictions seriously, but do not claim medical or "
    "allergen safety. Treat the budget as a preference for additional "
    "purchases. Return recipe names and ingredient names only. Do not return "
    "prices, totals, instructions, or other fields."
)
_SERVICE_UNAVAILABLE_MESSAGE = (
    "Recipe generation is temporarily unavailable. Please try again."
)


class GeneratedRecipe(TypedDict):
    name: str
    ingredients: list[str]


def generate_recipes(
    ingredients: list[str],
    budget: float,
    dietary_restrictions: list[str],
) -> list[GeneratedRecipe]:
    """Generate validated recipe names and ingredient lists via OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RecipeGenerationServiceError(
            "Live recipe generation is not configured. Please contact the "
            "application administrator.",
            status_code=503,
            log_message="OPENAI_API_KEY is not configured.",
        )

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip()
    if not model:
        raise RecipeGenerationServiceError(
            "Live recipe generation is not configured. Please contact the "
            "application administrator.",
            status_code=503,
            log_message="OPENAI_MODEL must not be empty.",
        )

    timeout = _read_timeout()
    client = OpenAI(
        api_key=api_key,
        timeout=timeout,
        max_retries=0,
    )
    request_input = [
        {"role": "system", "content": _SYSTEM_INSTRUCTIONS},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "available_ingredients": ingredients,
                    "budget_usd": budget,
                    "dietary_restrictions": dietary_restrictions,
                }
            ),
        },
    ]

    for attempt in range(1, MAX_TOTAL_ATTEMPTS + 1):
        try:
            response = client.responses.create(
                model=model,
                input=request_input,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "recipe_recommendations",
                        "strict": True,
                        "schema": _RECIPE_SCHEMA,
                    }
                },
            )
        except RateLimitError as error:
            _wait_or_raise(error, attempt)
            continue
        except APIConnectionError as error:
            _wait_or_raise(error, attempt)
            continue
        except APIStatusError as error:
            if error.status_code in {401, 403}:
                raise RecipeGenerationServiceError(
                    "Live recipe generation is not configured. Please contact "
                    "the application administrator.",
                    status_code=503,
                    log_message=(
                        "OpenAI rejected the configured credentials or access "
                        f"(HTTP {error.status_code})."
                    ),
                ) from error
            if _is_retryable_status(error.status_code):
                _wait_or_raise(error, attempt)
                continue
            raise RecipeGenerationServiceError(
                _SERVICE_UNAVAILABLE_MESSAGE,
                status_code=502,
                log_message=(
                    "OpenAI rejected the recipe request "
                    f"(HTTP {error.status_code})."
                ),
            ) from error
        except OpenAIError as error:
            raise RecipeGenerationServiceError(
                _SERVICE_UNAVAILABLE_MESSAGE,
                status_code=503,
                log_message=(
                    "OpenAI SDK request failed "
                    f"({type(error).__name__})."
                ),
            ) from error

        return _parse_response(response.output_text)

    raise AssertionError("The bounded OpenAI retry loop exited unexpectedly.")


def _read_timeout() -> float:
    value = os.getenv("OPENAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        timeout = float(value)
    except ValueError as error:
        raise RecipeGenerationServiceError(
            "Live recipe generation is not configured. Please contact the "
            "application administrator.",
            status_code=503,
            log_message="OPENAI_TIMEOUT_SECONDS must be a positive number.",
        ) from error

    if (
        not math.isfinite(timeout)
        or timeout <= 0
        or timeout > MAX_TIMEOUT_SECONDS
    ):
        raise RecipeGenerationServiceError(
            "Live recipe generation is not configured. Please contact the "
            "application administrator.",
            status_code=503,
            log_message=(
                "OPENAI_TIMEOUT_SECONDS must be greater than 0 and no more "
                f"than {MAX_TIMEOUT_SECONDS:g}."
            ),
        )
    return timeout


def _is_retryable_status(status_code: int) -> bool:
    return status_code in {408, 409, 429} or 500 <= status_code <= 599


def _wait_or_raise(error: Exception, attempt: int) -> None:
    if attempt >= MAX_TOTAL_ATTEMPTS:
        raise RecipeGenerationServiceError(
            _SERVICE_UNAVAILABLE_MESSAGE,
            status_code=503,
            log_message=(
                "Transient OpenAI failure after "
                f"{attempt} total attempt(s) ({type(error).__name__})."
            ),
        ) from error

    time.sleep(min(2 ** (attempt - 1), 8))


def _parse_response(output_text: object) -> list[GeneratedRecipe]:
    if not isinstance(output_text, str) or not output_text.strip():
        raise RecipeGenerationServiceError(
            "Recipe generation returned an invalid response. Please try again.",
            status_code=502,
            log_message="OpenAI returned no structured recipe text.",
        )

    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as error:
        raise RecipeGenerationServiceError(
            "Recipe generation returned an invalid response. Please try again.",
            status_code=502,
            log_message="OpenAI returned malformed JSON.",
        ) from error

    if not isinstance(payload, dict) or set(payload) != {"recipes"}:
        raise _invalid_response("The recipe response has an invalid object shape.")

    recipes = payload["recipes"]
    if (
        not isinstance(recipes, list)
        or not recipes
        or len(recipes) > MAX_RECIPES
    ):
        raise _invalid_response("The recipe response has an invalid recipe count.")

    validated_recipes: list[GeneratedRecipe] = []
    for recipe in recipes:
        if (
            not isinstance(recipe, dict)
            or set(recipe) != {"name", "ingredients"}
        ):
            raise _invalid_response("A recipe has an invalid object shape.")

        name = recipe["name"]
        recipe_ingredients = recipe["ingredients"]
        if not isinstance(name, str) or not name.strip():
            raise _invalid_response("A recipe name is empty or invalid.")
        if (
            not isinstance(recipe_ingredients, list)
            or not recipe_ingredients
            or len(recipe_ingredients) > MAX_INGREDIENTS_PER_RECIPE
            or any(
                not isinstance(ingredient, str) or not ingredient.strip()
                for ingredient in recipe_ingredients
            )
        ):
            raise _invalid_response("A recipe ingredient list is invalid.")

        validated_recipes.append(
            {
                "name": name.strip(),
                "ingredients": [
                    ingredient.strip() for ingredient in recipe_ingredients
                ],
            }
        )
    return validated_recipes


def _invalid_response(log_message: str) -> RecipeGenerationServiceError:
    return RecipeGenerationServiceError(
        "Recipe generation returned an invalid response. Please try again.",
        status_code=502,
        log_message=log_message,
    )
