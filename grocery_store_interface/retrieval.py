"""Local fixture retrieval and the replaceable HTML-page retrieval boundary."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pricing_timing import measure_stage

from .errors import GroceryPricingError


FIXTURE_PAGE = Path(__file__).parent / "fixtures" / "product-search.html"


class HtmlPageRetriever(Protocol):
    """Return a product-search page for one ingredient requirement."""

    def retrieve_page(self, ingredient_name: str) -> str:
        """Retrieve HTML without deciding how its product data is interpreted."""


class FixturePageRetriever:
    """Read the clearly labeled coursework product-listing fixture."""

    def __init__(self, page_path: Path = FIXTURE_PAGE) -> None:
        self._page_path = page_path

    def retrieve_page(self, ingredient_name: str) -> str:
        if not ingredient_name.strip():
            raise GroceryPricingError(
                "A product listing could not be prepared for an ingredient.",
                status_code=503,
                log_message="HTML fixture retrieval received a blank ingredient.",
            )

        try:
            with measure_stage("fixture_page_retrieval"):
                return self._page_path.read_text(encoding="utf-8")
        except OSError as error:
            raise GroceryPricingError(
                "The local coursework product fixture is unavailable.",
                status_code=503,
                log_message="HTML coursework fixture could not be read.",
            ) from error
