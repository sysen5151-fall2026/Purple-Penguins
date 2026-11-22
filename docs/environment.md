# Environment 
Language / version: Python 3.12  
Runtime:            local, virtual environment  
Model runner:       VS Code AI
Model:              GPT-5 mini
Editor:             VS Code  
Assistants in use:  All - ChatGPT, Z. Adornato - VS Code AI

## Optional OpenAI recipe-generation configuration

Recipe generation defaults to the local deterministic stub. To use the OpenAI API, configure these variables in the server process environment:

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `RECIPE_GENERATION_MODE` | No | `stub` | Select `stub` or `openai`. |
| `OPENAI_API_KEY` | For `openai` mode | None | Server-side API credential. Never place it in frontend code or commit it. |
| `OPENAI_MODEL` | No | `gpt-6-luna` | OpenAI model used for structured recipe generation. |
| `OPENAI_TIMEOUT_SECONDS` | No | `30` | Per-attempt timeout; accepted range is greater than 0 and at most 120 seconds. |

The application does not load `.env` files. `.env` files are ignored by Git; configure secrets through the operating system, deployment platform, or a secret manager. Live mode sends user-provided ingredients, budget, and dietary restrictions to OpenAI. Recipe generation has a maximum of ten total attempts for transient failures. The integration does not enforce an application-wide spend limit or cache recommendations.

## Grocery pricing

The current default, `GROCERY_PRICING_MODE=html_fixture`, reads local
coursework product-listing pages from
`grocery_store_interface/fixtures/`. The markup and prices are project-owned
test data, not retailer pages or live prices. This mode exercises the HTML
retrieval boundary, parser, product extraction/matching, unit normalization,
and package-cost calculation without external requests.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROCERY_PRICING_MODE` | No | `html_fixture` | Select `html_fixture`, `kroger`, explicit deterministic `stub`, or disabled `html_live` |
| `KROGER_CLIENT_ID` | For `kroger` | None | Registered Kroger application client ID |
| `KROGER_CLIENT_SECRET` | For `kroger` | None | Server-side Kroger application secret |
| `KROGER_LOCATION_ID` | For `kroger` | None | Eight-character store location used to obtain price and availability |
| `GROCERY_PRICING_TIMEOUT_SECONDS` | No | `10` | Per-request timeout; accepted range is greater than 0 and at most 60 seconds |

`GROCERY_PRICING_MODE=stub` uses the historical fixed-price dictionary,
including its `$1.00` fallback for unknown names. It is disclosed as
demonstration data and does not contain package details. V2 package totals are
unavailable in stub mode rather than inferred from use-cost values.

`GROCERY_PRICING_MODE=kroger` uses the documented Kroger Products API and
OAuth 2.0 client-credentials flow. Register an application with
[Kroger Developers](https://developer.kroger.com/); keep its client ID and
secret in the server environment and never log or expose them to the browser.
Each distinct ingredient search includes the configured `filter.locationId`.
The API response supplies product names, categories, item prices, package
sizes, and sold-by units. Matching, quantity conversion, and whole-package
purchase costs are calculated locally. Kroger pricing is an API source, not
HTML scraping.

The adapter makes one token request per pricing workflow and one search per
distinct ingredient, with a maximum of 25 distinct searches per workflow and
at most 20 results per search. Requests are paced by at least one second;
failures, timeouts, and HTTP 429 responses are surfaced without automatic
retry or fallback to fixtures/stub prices. Responses are not cached or
persisted. The adapter treats the U.S. API prices as USD when no currency
field is returned.

The shared matcher requires the requested ingredient phrase, checks product
categories and known prepared-food modifiers, and rejects multiple distinct
product IDs as ambiguous. Package variants under the same product ID are
selected deterministically by whole-package outlay for the recipe quantity,
then normalized use cost. Weight-sold items and unsupported package units fail
instead of producing an estimated price.

Kroger matching failures log only a sanitized requested ingredient label,
candidate/relevance counts, and a failure category. Provider response bodies,
credentials, access tokens, and authorization headers are not logged; the
public API continues to return its generic backend-failure schema.

`GROCERY_PRICING_MODE=html_live` is deliberately disabled and fails before
retrieval. It does not read a source URL or issue HTTP requests. The separate
`kroger` mode is the only currently configured live grocery source and uses
the documented public Products API, not a private API or HTML scraper. The
`HtmlPageRetriever` protocol remains available for the local fixture
demonstration; no live HTML source is configured.

Kroger's [acceptable-use rules](https://developer.kroger.com/documentation/public/getting-started/acceptable-use)
prohibit systematic harvesting to build a product catalog and cross-retailer
price comparisons. Recipe Roulette uses per-request lookups, stores no product
catalog, and does not compare retailers. Ingredients sent to Kroger can
include names that match user-owned items; the user's ownership list, budget,
and dietary restrictions are not sent. API daily quotas can apply; respect
HTTP 429 and do not increase request volume without reviewing the current
Kroger API guidance.

Fixture and Kroger modes share conservative product matching, unit conversion,
ingredient-use pricing, and v2 package calculations. Both reject ambiguous
product identities, known prepared/unrelated matches, missing or malformed
prices, unsupported package sizes, and incompatible units. Automated tests
mock all Kroger HTTP requests and use saved HTML fixtures; no live Kroger or
paid OpenAI request is made by pytest. The app does not load `.env` files.