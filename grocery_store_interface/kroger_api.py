"""Kroger Products API client using OAuth client credentials."""

from __future__ import annotations

import base64
import json
import math
import os
import re
import threading
import time
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pricing_timing import measure_stage, record_external_request

from .errors import GroceryPricingError
from .models import ProductCandidate


_API_BASE = "https://api.kroger.com/v1"
_TOKEN_URL = f"{_API_BASE}/connect/oauth2/token"
_PRODUCT_URL = f"{_API_BASE}/products"
_DEFAULT_TIMEOUT_SECONDS = 10.0
_MIN_REQUEST_INTERVAL_SECONDS = 1.0
_MAX_PRODUCTS_PER_SEARCH = 20
_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        response: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


class KrogerProductClient:
    """Fetch location-specific product results; do not persist provider data."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        location_id: str,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._location_id = location_id
        self._timeout_seconds = timeout_seconds
        self._access_token = ""

    @classmethod
    def from_environment(cls) -> KrogerProductClient:
        client_id = os.getenv("KROGER_CLIENT_ID", "").strip()
        client_secret = os.getenv("KROGER_CLIENT_SECRET", "").strip()
        location_id = os.getenv("KROGER_LOCATION_ID", "").strip()
        if not client_id or not client_secret or not location_id:
            raise GroceryPricingError(
                "Live Kroger pricing is not configured. Please contact the "
                "application administrator.",
                status_code=503,
                log_message=(
                    "KROGER_CLIENT_ID, KROGER_CLIENT_SECRET, and "
                    "KROGER_LOCATION_ID are required."
                ),
            )
        if len(location_id) != 8:
            raise GroceryPricingError(
                "Live Kroger pricing is not configured correctly.",
                status_code=503,
                log_message="KROGER_LOCATION_ID must be an 8-character ID.",
            )

        timeout_text = os.getenv(
            "GROCERY_PRICING_TIMEOUT_SECONDS",
            str(_DEFAULT_TIMEOUT_SECONDS),
        )
        try:
            timeout_seconds = float(timeout_text)
        except ValueError as error:
            raise GroceryPricingError(
                "Live Kroger pricing is not configured correctly.",
                status_code=503,
                log_message="GROCERY_PRICING_TIMEOUT_SECONDS is invalid.",
            ) from error
        if (
            not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or timeout_seconds > 60
        ):
            raise GroceryPricingError(
                "Live Kroger pricing is not configured correctly.",
                status_code=503,
                log_message=(
                    "GROCERY_PRICING_TIMEOUT_SECONDS must be greater than "
                    "0 and no more than 60."
                ),
            )

        return cls(
            client_id,
            client_secret,
            location_id,
            timeout_seconds=timeout_seconds,
        )

    def search_products(self, ingredient_name: str) -> list[ProductCandidate]:
        if (
            not ingredient_name.strip()
            or len(re.findall(r"[a-z0-9]+", ingredient_name.casefold())) > 8
        ):
            raise GroceryPricingError(
                "A Kroger product search could not be prepared for an "
                "ingredient.",
                status_code=503,
                log_message="Kroger search term was blank or exceeded 8 words.",
            )

        query = urlencode(
            {
                "filter.term": ingredient_name,
                "filter.locationId": self._location_id,
                "filter.limit": _MAX_PRODUCTS_PER_SEARCH,
            }
        )
        response = self._request_json(
            Request(
                f"{_PRODUCT_URL}?{query}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._get_access_token()}",
                    "User-Agent": "Recipe-Roulette-Chapter-11",
                },
                method="GET",
            ),
            operation="product_search",
        )
        products = response.get("data")
        if not isinstance(products, list) or any(
            not isinstance(product, dict) for product in products
        ):
            raise GroceryPricingError(
                "Live Kroger pricing returned incomplete product data.",
                status_code=502,
                log_message=(
                    "Kroger product response did not contain a valid data list."
                ),
            )
        return _product_candidates(products)

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode("utf-8")
        ).decode("ascii")
        request = Request(
            _TOKEN_URL,
            data=urlencode(
                {
                    "grant_type": "client_credentials",
                    "scope": "product.compact",
                }
            ).encode("ascii"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Recipe-Roulette-Chapter-11",
            },
            method="POST",
        )
        response = self._request_json(request, operation="token")
        token = response.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise GroceryPricingError(
                "Live Kroger pricing is temporarily unavailable.",
                status_code=503,
                log_message="Kroger token response omitted an access token.",
            )
        self._access_token = token.strip()
        return self._access_token

    def _request_json(
        self,
        request: Request,
        *,
        operation: str,
    ) -> dict[str, Any]:
        _pace_requests()
        record_external_request()
        try:
            with measure_stage("kroger_http_request"):
                with _open_request(
                    request,
                    timeout_seconds=self._timeout_seconds,
                ) as response:
                    body = response.read()
        except HTTPError as error:
            raise _http_error(error, operation) from error
        except (URLError, TimeoutError, OSError) as error:
            raise GroceryPricingError(
                "Live Kroger pricing is temporarily unavailable. Please try "
                "again later.",
                status_code=503,
                log_message=f"Kroger {operation} request failed or timed out.",
            ) from error

        try:
            with measure_stage("kroger_response_parsing"):
                payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GroceryPricingError(
                "Live Kroger pricing returned incomplete information.",
                status_code=502,
                log_message=f"Kroger {operation} response was not valid JSON.",
            ) from error
        if not isinstance(payload, dict):
            raise GroceryPricingError(
                "Live Kroger pricing returned incomplete information.",
                status_code=502,
                log_message=f"Kroger {operation} response was not a JSON object.",
            )
        return payload


def _product_candidates(
    products: list[dict[str, Any]],
) -> list[ProductCandidate]:
    with measure_stage("kroger_product_extraction"):
        candidates: list[ProductCandidate] = []
        for product in products:
            description_value = product.get("description")
            description = (
                description_value.strip()
                if isinstance(description_value, str)
                else ""
            )
            product_id = _text_value(product.get("productId"))
            brand = _text_value(product.get("brand")) or ""
            categories = _category_labels(product.get("categories"))
            items = product.get("items")
            if not isinstance(items, list) or not items:
                candidates.append(
                    ProductCandidate(
                        description=description,
                        product_id=product_id,
                        item_id="",
                        brand=brand,
                        categories=categories,
                        price_text=None,
                        package_size_text=None,
                        sold_by=None,
                        currency=None,
                    )
                )
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                price_text, currency = _item_price_fields(item.get("price"))
                candidates.append(
                    ProductCandidate(
                        description=description,
                        product_id=product_id,
                        item_id=_text_value(item.get("itemId")) or "",
                        brand=brand,
                        categories=categories,
                        price_text=price_text,
                        package_size_text=_text_value(item.get("size")),
                        sold_by=_text_value(item.get("soldBy")),
                        currency=currency,
                    )
                )
        return candidates


def _item_price_fields(price_data: object) -> tuple[str | None, str | None]:
    if not isinstance(price_data, dict):
        return None, None

    currency_value = price_data.get("currency", "USD")
    currency = (
        currency_value.strip().upper()
        if isinstance(currency_value, str)
        else None
    )
    regular = _positive_decimal(price_data.get("regular"))
    promo = _positive_decimal(price_data.get("promo"))
    if regular is None:
        selected = promo
    elif promo is not None and promo < regular:
        selected = promo
    else:
        selected = regular
    return (str(selected) if selected is not None else None), currency


def _positive_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount <= 0:
        return None
    return amount


def _text_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _category_labels(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    labels: list[str] = []
    for category in value:
        if isinstance(category, str) and category.strip():
            labels.append(category.strip())
        elif isinstance(category, dict):
            for key in ("name", "description", "categoryName"):
                label = _text_value(category.get(key))
                if label:
                    labels.append(label)
                    break
    return tuple(labels)


def _http_error(error: HTTPError, operation: str) -> GroceryPricingError:
    status = error.code
    if status == 429:
        return GroceryPricingError(
            "Kroger is rate-limiting pricing requests. Please try again later.",
            status_code=503,
            log_message=f"Kroger {operation} request was rate limited (HTTP 429).",
            provider_status_code=status,
        )
    if status in {401, 403}:
        return GroceryPricingError(
            "Kroger pricing is not authorized. Please contact the "
            "application administrator.",
            status_code=503,
            log_message=(
                f"Kroger {operation} request was not authorized (HTTP {status})."
            ),
            provider_status_code=status,
        )
    return GroceryPricingError(
        "Live Kroger pricing is temporarily unavailable. Please try again.",
        status_code=502 if 400 <= status < 500 else 503,
        log_message=f"Kroger {operation} request failed (HTTP {status}).",
        provider_status_code=status,
    )


def _open_request(request: Request, *, timeout_seconds: float) -> Any:
    opener = build_opener(_NoRedirectHandler())
    return opener.open(request, timeout=timeout_seconds)


def _pace_requests() -> None:
    global _LAST_REQUEST_AT
    with _REQUEST_LOCK:
        now = time.monotonic()
        delay = _MIN_REQUEST_INTERVAL_SECONDS - (now - _LAST_REQUEST_AT)
        if delay > 0:
            with measure_stage("kroger_request_pacing"):
                time.sleep(delay)
        _LAST_REQUEST_AT = time.monotonic()
