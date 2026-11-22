"""Parse the controlled HTML product-card structure used by local fixtures."""

from __future__ import annotations

from html.parser import HTMLParser

from .errors import GroceryPricingError


_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class _ProductCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, str | None]] = []
        self.tag_stack: list[str] = []
        self.malformed = False

    def handle_starttag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
    ) -> None:
        if tag not in _VOID_TAGS:
            self.tag_stack.append(tag)
        values = dict(attributes)
        if "data-product-card" not in values:
            return

        self.cards.append(
            {
                "description": values.get("data-name"),
                "product_id": values.get("data-product-id"),
                "item_id": values.get("data-item-id"),
                "brand": values.get("data-brand"),
                "categories": values.get("data-categories"),
                "price": values.get("data-price"),
                "package_size": values.get("data-package-size"),
                "sold_by": values.get("data-sold-by"),
                "currency": values.get("data-currency"),
            }
        )

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_TAGS:
            self.malformed = True
            return
        if not self.tag_stack or self.tag_stack[-1] != tag:
            self.malformed = True
            return
        self.tag_stack.pop()


def parse_product_listing_html(html_text: str) -> list[dict[str, str | None]]:
    """Parse product cards; reject empty pages or unsupported page structure."""
    if not isinstance(html_text, str) or not html_text.strip():
        raise _malformed_listing()

    parser = _ProductCardParser()
    try:
        parser.feed(html_text)
        parser.close()
    except (AssertionError, ValueError) as error:
        raise _malformed_listing() from error

    if parser.malformed or parser.tag_stack or not parser.cards:
        raise _malformed_listing()
    return parser.cards


def _malformed_listing() -> GroceryPricingError:
    return GroceryPricingError(
        "The product listing could not be read in the expected HTML format.",
        status_code=502,
        log_message="HTML page did not contain supported product cards.",
    )
