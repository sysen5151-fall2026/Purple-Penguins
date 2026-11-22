# ADR 0002 — Kroger Products API pricing source

- Date: 2026-11-22
- Status: accepted; live mode is opt-in and awaits separately approved testing

## Context

The original S.1 model is titled Webscraping and includes webpage request,
receipt, parsing, and price-extraction actions. The team has now selected the
official Kroger Products API as the final live pricing source. This is an
architectural source substitution: Kroger returns location-filtered JSON, not
retailer HTML.

The project retains local HTML fixtures to demonstrate the earlier scraping
pipeline and the deterministic in-memory dictionary for offline tests. The
default `GROCERY_PRICING_MODE=html_fixture` remains non-live until the team
separately enables and tests Kroger mode.

## Alternatives and evidence

- **Literal retailer HTML scraping:** No retailer was verified as permitting
  the intended automated product lookup while returning the needed prices,
  package quantities, and units in ordinary HTML.
- **Kroger Products API:** Official documentation describes product search,
  `filter.term`, `filter.locationId`, product price, size, and sold-by fields.
  The Quick Start documents registered client credentials and OAuth 2.0
  client-credentials authentication.
- **Open Prices:** The public price dataset is licensed under ODbL and offers
  documented API/data exports, but its normal website HTML is a JavaScript app
  shell. Its crowd-sourced observations are not live retailer inventory. Using
  it would be a separate data/API architecture.
- **In-memory dictionary and HTML fixtures:** Retained as offline sources.
  `html_fixture` remains the default; fixture prices are illustrative and the
  explicit `stub` mode keeps the historical `$1.00` fallback.

Kroger's [Product Search reference](https://developer.kroger.com/documentation/api-products/public/products/product-search?beta=true),
[OAuth Quick Start](https://developer.kroger.com/documentation/public/), and
[Acceptable Use rules](https://developer.kroger.com/documentation/public/getting-started/acceptable-use)
are the source evidence. Kroger's rules prohibit systematic response
harvesting to build a catalog and cross-retailer price comparisons. Public API
daily quotas may apply; the implementation does not assume a vendor quota and
surfaces HTTP 429 without retrying.

## Decision

- Implement Kroger's documented `POST /v1/connect/oauth2/token` client-
  credentials flow and `GET /v1/products` product search.
- Require server-side `KROGER_CLIENT_ID`, `KROGER_CLIENT_SECRET`, and
  `KROGER_LOCATION_ID`. The location filter is required for product price and
  availability. Do not send the user's budget, dietary restrictions, or
  ownership list.
- Keep `GROCERY_PRICING_MODE=html_fixture` as the safe default until live
  credentials/location are reviewed and the team explicitly enables `kroger`.
  Preserve `stub` mode. Keep `html_live` disabled.
- Never fall back from Kroger failure to fixture or stub prices. Treat auth
  failure, timeout, 429, malformed response, missing price/package data,
  ambiguous identity, and incompatible units as explicit pricing failures.
- Match exact requested varieties/forms conservatively; allow controlled
  aliases and valid categories to establish relevance only when product
  descriptions do not contradict them. Reject prepared or unrelated products.
- For generic ingredients, select across distinct product IDs only when they
  represent comparable substitutes. Prefer unrequested standard products over
  specialty variants, then rank by a reasonable whole-package fit. Resolve
  equivalent package variants within a product identity and use normalized
  description, brand, product ID, and item ID as deterministic tie-breakers.
  Actual price is consulted only as a final tie-break for otherwise identical
  offer records, never as the primary selection criterion. Return an explicit
  pricing failure when the remaining candidates are materially ambiguous.
- Emit internal sanitized matching diagnostics with the requested ingredient,
  candidate/relevance/priceable counts, selection reason and product ID, or
  failure category. Do not log credentials, tokens, authorization headers, or
  raw provider responses.
- Reuse the common product candidate, category/identity matching, unit
  conversion, recipe-use calculation, and v2 whole-package calculations. Do
  not persist or cache API product responses. Pace requests locally and cap
  each pricing workflow at 25 distinct ingredient searches.
- Preserve the v1 request/response semantics and v2 fields. V2 package cost
  remains `ceil(recipe quantity / package quantity) × package price`, for
  unowned ingredients only and independently per alternative recipe.
- Preserve the original swing-weight matrix and scores. Record the Kroger
  selection as a new decision/rationale; revise modeled alternatives or
  scores only through the team's explicit trade-study revision process.

## Consequences and Innoslate updates

The API source is not equivalent to literal S.1 webpage scraping. Revise the
S.1 scenario/sequence to represent the Kroger API participant and its token,
location-filtered search, JSON response, local extraction/matching, and error
flows. Replace or revise the webpage request/receipt and parse actions; keep
the UI display/receive actions if their interfaces remain unchanged. Allocate
any new authentication action/ICOMs and participant IDs in Innoslate rather
than inventing them in code documentation.

Benchmark `kroger_http_request` timings measure OAuth/product API round trips,
not webpage response latency. Preserve local HTML fixture timings as a
separate scenario and do not overwrite historical Chapter 10/11 measurement
files.

## Controlled live validation

`scripts/smoke_test_kroger.py --live` performs one ingredient lookup and has a
hard request budget of two: one OAuth token request and one product search.
It requires the confirmation phrase `RUN ONE KROGER SMOKE TEST WITH CAP 2`.
It was not executed as part of this implementation. A 30-run, five-ingredient
benchmark is capped at 180 HTTP requests (30 × (one token + five searches))
and separately requires `--live`, an explicit cap, and interactive
confirmation.
