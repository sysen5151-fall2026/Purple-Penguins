# Recipe Roulette — Product Specification

**Project:** Recipe Roulette (Purple Penguins)  
**Document status:** Draft for team review; maintained through Chapter 11 against the current repository and `Recipe Roulette Export.xml` as of 2026-11-22.
**Source of truth for interfaces:** `contracts/api-v1.yaml`; **source of truth for approved needs/requirements:** Innoslate. This document captures both the modeled target and actual prototype behavior. A proposed criterion is **not** an approved requirement until reviewed and reconciled in Innoslate.

## 1. Purpose, scope, and system context

Recipe Roulette helps users find recipes from available ingredients while considering dietary preferences and a monetary budget. Its current implementation is a Flask web application with a JSON recipe API, a default deterministic recipe-generation stub, optional hosted OpenAI recipe generation, local HTML fixture pricing by default, an explicit deterministic price stub, and an opt-in Kroger Products API integration. The API is a retailer source substitution, not literal webpage scraping. The current build is **not** a production recipe safety, nutritional, or verified live-pricing service.

**System boundary:** The App accepts user ingredients, budget, and dietary restrictions; it sends a recipe request to a configured generation interface, retrieves ingredient price estimates from its grocery-store interface, calculates estimated full and additional-purchase costs, and displays results. External boundaries represented in the model include the User, LLM API, Grocery Store, and Customer Service. Pricing defaults to local coursework HTML fixtures; explicitly configured Kroger mode makes location-filtered API requests. Account login is simulated. See `docs/context.md`, `docs/traceability.md`, and `docs/route-table.md` for current project artifacts.

## 2. Needs and Acceptance Criteria

### 2.1 Stakeholder needs, traced requirements, and measurable acceptance criteria

The identifiers and stakeholder requirement wording below are drawn from the supplied Innoslate export. The **acceptance criteria** are proposed testable expressions of the modeled needs unless already specified numerically by the requirement. **Status** distinguishes current repository evidence from future target behavior. Tests must be linked to these identifiers in `docs/traceability.md`.

| Need ID and need | Related stakeholder requirement | Acceptance criterion / measure | Current status |
| --- | --- | --- | --- |
| `SN.1.1` Quick Recipe Generation | `STH.1.1.1` — The system shall allow users to submit ingredients and dietary restrictions as recipe-generation inputs. | Given valid inputs, the UI submits ingredients, budget and restrictions through `POST /api/v1/recipes`; the API returns its documented response schema. | Implemented in the browser/API; not a complete live end-to-end test. |
| `SN.1.2` Tailored Recipes | `STH.1.1.2` — The system shall generate recipes based on user-provided inputs, conforming to the user's stored dietary restrictions/preferences. | For a defined, reviewed set of dietary examples, generated results contain no ingredients prohibited by the supplied restrictions. **Proposed criterion; test set and threshold need approval.** | Not guaranteed. Stub recipes are fixed; live model is prompted to consider restrictions but does not guarantee compliance. No stored preferences. |
| `SN.1.11` Affordable meal recommendations | `STH.1.1.8` — The system shall allow users to specify a meal budget when generating recipes. | Given a positive budget in USD, the API accepts it and returns `within_budget` based on `additional_purchase_cost <= budget`. | Implemented for cost comparison using stub prices; recommendations are not filtered to budget. |
| `SN.1.11` Affordable meal recommendations | `STH.1.1.9` — The system shall generate recipes with an estimated total ingredient cost that does not exceed the user-specified budget by more than 5%. | For each generated recommendation, `estimated_total_cost <= 1.05 × budget`, measured against the specified pricing source. | **Gap:** Current code compares *additional-purchase cost*, not full estimated ingredient cost, and may return over-budget recipes. Keep this requirement distinct from the existing `within_budget` field. |
| `SN.1.3` Easy Recipes | `STH.1.1.3` — The system shall generate recipes that include ingredient lists and step-by-step preparation instructions. | Each returned recipe includes a nonempty ingredient list and ordered, nonempty preparation instructions. | **Gap:** Current response includes ingredient lists, not instructions. |
| `SN.2.1` Reliable Connection to API | `STH.1.1.13` — The system shall integrate with the AI LLM API to generate recipes. | In configured live mode, a valid request returns a schema-valid recipe list from the designated model; unavailable or malformed responses fail safely. | Implemented as optional adapter; successful live operation is not established by offline tests. |
| `SN.2.1` Reliable Connection to API | `STH.1.1.14` — The system shall retry a recipe-generation API request following a transient API communication failure, up to 10 retry attempts. | Fault-injection test counts retries and confirms that transient errors are retried and permanent/schema errors are not. **Resolve model wording:** current implementation permits **10 total attempts**, not 10 retries after the first attempt. | Implemented with ten **total** attempts; model discrepancy needs resolution. |
| `SN.1.10` Serving Size Adjustments | `STH.1.1.10` / `STH.1.1.12` — serving selection and quantity recalculation | For valid serving-count changes, all ingredient quantities scale in proportion to the new number of servings. | Deferred; internal recipe quantities support price normalization, but servings and quantity adjustment are absent from the v1 API. |
| `SN.1.4` Save Recipes; `SN.1.7` Search for Previous Recipes | `STH.1.1.4` / `STH.1.1.6` — save and search | Saved recipes can be retrieved by the authenticated user and searched by a defined query, with persistence across process restarts. | Deferred; no persistent user recipe store or authentication. |
| `SN.1.8` Generate Shopping Lists | `STH.1.1.7` — The system shall generate shopping lists from recipe ingredients. | For a selected recipe, a shopping list enumerates required ingredients and distinguishes user-owned ingredients from items to purchase. | Partial data available (`owned` flags and purchase cost); no dedicated editable shopping-list feature. |
| `SN.1.9` Secure Personal Data | `STH.1.3.1` / `STH.1.3.2` — authentication and encrypted account information | Saved-recipe access requires authentication; any stored sensitive account information is encrypted. | Deferred; no real accounts or sensitive-account storage in this prototype. |
| `SN.2.12` Reliable System Availability | `STH.1.3.5` — The system shall maintain an application availability of at least 99%. | In a defined measurement interval, observed availability is ≥99%, with an agreed monitoring method. | Target only; no availability measurement evidence. |
| `SN.1.1` Quick Recipe Generation | `STH.1.3.3` — The system shall generate a recipe within 10 seconds of a user's request under normal operating conditions. | Measure elapsed time from valid submission to completed recipe response; each sampled request meets 10 seconds under a team-defined normal-load test profile. | Target only; no accepted timing benchmark. Live adapter permits a 30-second default per-attempt timeout and retries. |

**Other modeled needs not currently delivered:** recipe editing (`SN.1.5`), nutrition information (`SN.1.6`), ingredient substitutions (`SN.1.12`), scaling (`SN.2.5`), API usage/cost tracking (`SN.2.6`), monitoring/administration (`SN.2.8`, `SN.2.10`, `SN.2.11`), backups, and deployment availability. Their corresponding Innoslate requirements remain in scope for future design decisions; do not claim they are accepted or implemented on the basis of the current repository.

### 2.2 Current API acceptance tests (baseline behavior, not a replacement for stakeholder acceptance)

| Baseline check | Expected observable result | Evidence in repository |
| --- | --- | --- |
| Valid request | `POST /api/v1/recipes` returns HTTP 200 with a `recipes` array matching the contract. | `tests/test_functional_requirements.py` |
| Invalid/missing fields | Malformed JSON, absent required fields, invalid budget, or invalid ingredient/restriction entries return HTTP 400 `invalid_request` with field-specific detail as appropriate. | `tests/test_functional_requirements.py` |
| Owned ingredients | Case-insensitive exact-name match after stripping whitespace, plus a controlled compatibility rule for standard dry-pasta names/shapes. Incompatible or unrecognized forms remain unconfirmed. Owned ingredients are excluded from additional-purchase cost, not full recipe cost. | `tests/test_functional_requirements.py` |
| Budget flag | `within_budget` is true exactly when `additional_purchase_cost <= budget`. | `tests/test_functional_requirements.py` |
| Provider failures | No credentials/configuration → safe 503; unusable provider response → safe 502; server errors → safe backend failure without raw exception details. | `tests/test_openai_integration.py`; `user_interface/routes.py` |
| Retry behavior | Transient provider failures are retried with a maximum of 10 **total** attempts; malformed provider output is not retried. | `tests/test_openai_integration.py` |

## 3. Data Contract

### 3.1 Source inventory

| Source | Boundary and data | Refresh cadence | Unavailable/missing behavior | Status |
| --- | --- | --- | --- | --- |
| Browser user input | `ingredients` (`list[str]`), `budget` (`number`, USD), `dietary_restrictions` (`list[str]`) | Every user request | Invalid fields rejected with HTTP 400, no recipe generation initiated | Implemented |
| Recipe source — stub | Two fixed recipes with names and quantity-bearing ingredient requirements | Static until code update | Does not reflect submitted preferences; intended for deterministic testing | Implemented |
| Recipe source — hosted LLM | OpenAI Responses API returns names and ingredient names, quantities, and supported units | Per request, only in live mode | Missing key/access → 503; transient errors retried; invalid output → 502 | Optional implementation; live execution not verified here |
| Grocery pricing — Kroger Products API | Documented product search with location-specific prices/package data normalized to generated recipe quantities | Per recipe request; no product-price persistence | Missing/ambiguous product, invalid price/package data, API error, rate limit, or incompatible units returns a safe pricing failure; no fixture/stub fallback | Implemented as an opt-in live API source; no live call is implementation evidence |
| Grocery pricing — HTML fixtures | Saved local project-owned HTML cards with illustrative product name, package, unit, and price fields | Per recipe request; no external HTTP or price persistence | Missing/ambiguous product, invalid price/package data, malformed structure, or incompatible units returns a safe pricing failure | Implemented for fixture markup only; default mode |
| Grocery pricing — stub | Local dictionary with seven fixed demonstration prices, USD | Static until code update | Unknown names use the historical `$1.00` demo fallback | Explicit offline/test mode |
| Persistent user/recipe data | No database schema or persistent store in current repository | Not applicable | Saved recipes and login cannot be used | Not implemented |

**Chapter 11 source decision:** The team selected the Kroger Products API as the final live grocery-pricing source. Kroger is a documented API source substitution for S.1, not literal HTML webpage scraping. Local HTML fixtures remain the default until credentials and location configuration are explicitly enabled; fixture values are illustrative, not live prices. The in-memory dictionary remains available as explicit `stub` mode. See ADR 0002 and `docs/environment.md`.

### 3.2 REST input schema — `POST /api/v1/recipes`

Content type: `application/json`. The authoritative full schema is `contracts/api-v1.yaml`.

| Field | Type | Required | Validation / semantics |
| --- | --- | --- | --- |
| `ingredients` | array of nonempty strings | Yes | At least one ingredient. Represents ingredients **already owned** by the user; input strings are trimmed. |
| `budget` | finite number | Yes | Strictly greater than 0, in USD; boolean is not accepted as a number. |
| `dietary_restrictions` | array of nonempty strings | Yes | May be an empty array to indicate no restrictions; entries are trimmed. |

Unexpected top-level fields are rejected. **Servings are not included** in v1 because that capability is not implemented.

Example valid input:

```json
{
  "ingredients": ["pasta", "eggs"],
  "budget": 15.00,
  "dietary_restrictions": []
}
```

### 3.3 REST output schema and price calculations

HTTP 200 body: `{ "recipes": [ ... ] }`. Each recipe includes:

| Field | Type | Definition |
| --- | --- | --- |
| `name` | string | Generated/stub recipe title |
| `ingredients` | array of objects | Each object has `name: string`, `estimated_price: number` (USD ≥0 for the generated recipe quantity), and `owned: boolean` |
| `estimated_total_cost` | number, USD | Sum of **all** ingredient estimated prices, including owned items |
| `additional_purchase_cost` | number, USD | Sum of estimated prices for ingredients not marked `owned` |
| `within_budget` | boolean | Whether `additional_purchase_cost <= budget` |

Owned matching first uses case-insensitive exact-name matching after stripping surrounding whitespace. A controlled rule also treats generic pasta, dry pasta, and recognized standard dry-pasta shapes as compatible; fresh, stuffed, whole-wheat, and other unrecognized forms are not included. Other varieties/forms—including fresh versus canned tomatoes, salted versus unsalted butter, and whole versus 2% milk—are not inferred to be equivalent. Unconfirmed ownership is not assumed. Amounts already held are not considered. The public request/response field shapes remain unchanged. Internal recipe output includes a quantity/unit for each ingredient; Kroger package prices are converted only when package and recipe units are dimension-compatible. Full and additional-purchase costs are aggregated in cents with rounding to the nearest cent. Fixture prices are illustrative only and make no claim about current prices, availability, taxes, or checkout fees.

Error responses use `{ "error": { "code": "invalid_request" | "backend_failure", "message": "...", "field_errors": { ... }? } }`. Documented HTTP statuses are 400, 500, 502, and 503; see `contracts/api-v1.yaml` for details.

### 3.3.1 Version 2 package-purchase response

`POST /api/v2/recipes` accepts the same request schema and preserves every v1
success field. It additionally returns per-ingredient selected product/package
provenance, `additional_package_purchase_cost`, `within_package_budget`, and a
package-estimate status. Package outlay uses whole packages:
`ceil(required quantity / package quantity) × package price`, for unowned
ingredients only. Each recipe is an alternative; package totals are calculated
independently per recipe and are not combined into a shopping list.

V2 retains `estimated_total_cost`, `additional_purchase_cost`, and
`within_budget` as ingredient-use metrics. Package fields are `null` and
status is `unavailable` when package purchase information cannot be
established. Stub prices are not treated as package prices. The browser labels
consumption and package costs separately.

### 3.4 Missing data, abnormal values, and trust boundary

- A missing/malformed client request must return a 400 and must not be silently repaired.
- Provider output must be checked for schema compliance before the price lookup and response construction.
- Negative or non-finite prices must not be accepted for cost calculation.
- Kroger and HTML fixture modes do not silently assign fallback prices: an unmatched product or incompatible package unit fails the pricing request. Kroger failures do not fall back to fixtures/stub. The historical `$1.00` fallback is restricted to explicit offline stub mode.
- User ingredients, budget, and restrictions are transmitted to the hosted OpenAI provider only when `RECIPE_GENERATION_MODE=openai`. Do not transmit real or sensitive data without the approvals required by the lab manual.

## 4. Model Response Contract

### 4.1 Model purpose and inputs

The recipe model produces recipe names and ingredient requirements with a name,
positive quantity, and supported unit from the following inputs:
`available_ingredients: list[str]`, `budget_usd: number`, and
`dietary_restrictions: list[str]`. It does **not** return prices, instructions,
or nutritional information. Pricing remains a separate interface
responsibility. Quantities describe one generated recipe batch; servings are
still not part of the public request contract.

Default mode is `RECIPE_GENERATION_MODE=stub`; optional live mode is `openai`. Environment configuration is described in `README.md`. The model ID is read from `OPENAI_MODEL` (the repository has a configurable default); the server-side credential is `OPENAI_API_KEY` and must never be placed in the browser or committed to the repository.

### 4.2 Provider response schema

The live adapter requests strict structured JSON of the shape:

```json
{
  "recipes": [
    {
      "name": "Vegetable Stir-Fry",
      "ingredients": [
        {"name": "broccoli", "quantity": 1, "unit": "head"},
        {"name": "onions", "quantity": 1, "unit": "count"},
        {"name": "soy sauce", "quantity": 2, "unit": "fl_oz"}
      ]
    }
  ]
}
```

- The top-level object has exactly one property, `recipes`, an array.
- Each recipe has exactly `name` (nonempty string) and `ingredients` (an array of unique requirements with a nonempty `name`, positive finite `quantity`, and supported `unit`).
- No additional fields are accepted at either level. Prices, instructions, and totals are not generated by the model.
- The adapter limits output to **5 recipes** and **40 ingredients per recipe**; inspect the adapter for exact response-validation behavior.
- The successful public **REST** response is different: it enriches model results with the price and ownership fields in Section 3.3.

### 4.3 Configuration, timeouts, failures, and safety

| Aspect | Current implementation contract |
| --- | --- |
| Live provider | OpenAI Responses API via server-side SDK |
| Max output tokens | 4,096 for recipe generation; 2,048 for the isolated LLM pricing benchmark |
| Default per-attempt timeout | 30 seconds; configured via `OPENAI_TIMEOUT_SECONDS`, bounded above by 120 seconds |
| Retry limit | 10 **total** attempts on selected transient failures; SDK automatic retry disabled |
| Retryable failures | Connection and timeout failures, 408, 409, 429, and 5xx statuses (subject to adapter logic) |
| Non-retryable failure | Invalid schema/model output; unauthorized/configuration problems; other non-transient failures |
| Public error handling | Missing credentials/access → safe 503; bad provider response → safe 502; internal unexpected error → safe 500 |
| Dietary/allergen handling | Model prompted to consider restrictions; **no guaranteed dietary or allergen compliance**. Show the disclosure and do not label recommendations medically safe. |
| Provider cost | Live requests may incur usage charges and retries; the app has no implemented spend cap or usage dashboard. |

**Important discrepancy to resolve:** `STH.1.1.14` says “up to 10 retry attempts,” while the current code applies **10 total attempts**. The team must reconcile the model and implementation before signoff.

## 5. Model-to-code traceability and Chapter 9 component candidate

The current repository maps the following Innoslate functions to code:

| Innoslate function | Current implementation | State |
| --- | --- | --- |
| `F.2.4.1` Prepare Recipe Request | `recipe_service.prepare_recipe_request` | Implemented |
| `F.2.4.2` Format and Validate API Request | `recipe_service.format_and_validate_api_request` | Implemented; good Chapter 9 component candidate |
| `F.2.4.3` Specify Already-Owned Recipe Ingredients | `recipe_service.specify_already_owned_recipe_ingredients` | Implemented |
| `F.2.4.4` Submit Recipe and Pricing Requests | `recipe_service.submit_recipe_and_pricing_requests` | Implemented with optional live recipe generation and selectable Kroger API, local HTML fixture, or explicit dictionary stub pricing |

For a **Chapter 9 component implementation** using `C.2.4.2`, assemble the one-pass implementation prompt from the exact Innoslate component specification (verbatim requirement IDs/text, ICOMs, types, error cases, constraints and success criteria). Do not treat this consolidated `SPEC.md` as a substitute for that component-specific source. Compare the generated output against the specification **before** making corrections; record each deviation in `docs/deviation-log.md`, classify it, and reconcile justified changes with Innoslate and the tests. The current repository may already contain similar functionality, but its existence alone does not establish that the Chapter 9 procedure was followed.

## 6. Verification and release gates

1. Run `python -m pytest` in the Python 3.12 environment with `requirements.txt` installed; record the actual results, not assumed passes.
2. Ensure `.github/workflows/tests.yml` runs the test suite on pull requests and prevents a requirements-breaking change from being accepted.
3. For each approved stakeholder criterion, associate at least one named test and the related requirement in `docs/traceability.md`. Add acceptance tests for unmet requirements only when they become the scope of a build increment.
4. Verify API inputs and outputs against `contracts/api-v1.yaml`, including malformed and missing values.
5. Verify the hosted model adapter's response-validity, timeout, retries and failure-path behavior without requiring real provider calls in CI; perform separately authorized live integration checks.
6. Do not claim the 10-second recipe response, 99% availability, recipe-budget-compliance, nutrition, or data-security targets are achieved until measured and evidenced.
7. Before Chapter 9 completion, reconcile all requirement, component, test and code changes and complete the component deviation log.

## 7. Open decisions requiring team approval

- **Target versus prototype:** Decide which stakeholder requirements are in scope for this semester's product build versus intentionally deferred. Preserve deferred requirements in the model rather than rewriting them as completed capabilities.
- **Budget semantics:** The modeled requirement `STH.1.1.9` uses *total recipe ingredient-use cost* and permits at most a 5% overage. V1 `within_budget` remains additional ingredient-use cost; V2 adds `within_package_budget` for whole-package outlay. Decide which metric should govern the stakeholder requirement and reconcile the model, UI, and code.
- **Innoslate S.1 update:** The team selected Kroger's official Products API rather than literal scraping. Update the S.1 participants/actions to the approved API request/JSON response flow and document the source substitution in the swing-weight rationale; preserve original scores unless the team explicitly revises them.
- **Dietary restrictions:** Define a testable restriction taxonomy and validation policy, particularly for allergens. LLM prompting alone cannot guarantee compliance.
- **Preparation instructions and servings:** Recipe ingredient quantities now support price normalization internally. Decide whether to add servings, serving recalculation, preparation instructions, substitutions, or shopping-list fields to the public API.
- **Latency and reliability:** Approve the load profile and timing measurement method for the modeled 10-second recipe target and 99% availability target; reconcile the retry limit.
- **Storage/authentication:** Specify a persistent data source and account policy before enabling saved recipes or security claims.
- **Specification process:** Confirm requirement IDs and exact text against the current Innoslate model, map each to tests, and record the Chapter 9 one-pass component implementation/deviation log.

---

**References inside the project:** `Recipe Roulette(1).xml` (uploaded Innoslate model), `README.md`, `docs/context.md`, `docs/traceability.md`, `contracts/api-v1.yaml`, `recipe_service.py`, `llm_api_interface/openai_adapter.py`, `grocery_store_interface/__init__.py`, `tests/test_functional_requirements.py`, and `tests/test_openai_integration.py`.
