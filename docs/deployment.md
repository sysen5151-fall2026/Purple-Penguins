# Recipe Roulette — Component and Deployment View

**Project:** SYSEN 5151 — Recipe Roulette  
**Deliverable:** Chapter 8, `docs/deployment.md` (maintained through Chapter 11)
**Basis:** `Purple-Penguins-Phase_5_M2` repository snapshot and Recipe Roulette Innoslate architecture export (November 2026)  
**Status:** **Documented implementation**, not evidence of production deployment or verified live external services.

## 1. Purpose and system boundary

This document describes **what runs where and what communicates with what** for the current Recipe Roulette product build. It distinguishes implemented processes, in-process modules, locally simulated external systems, and the optional hosted LLM service. It also records where the implementation still differs from the system architecture and Chapter 8–9 objectives.

The system of interest is the Recipe Roulette application. A user supplies available ingredients, a budget (USD), and dietary restrictions; the application requests recipe candidates, obtains ingredient-use estimates, identifies ingredients the user already owns, computes package-purchase estimates, and presents results. Recipe generation defaults to a deterministic stub or can use OpenAI. Grocery pricing defaults to saved local HTML fixtures; Kroger Products API pricing is available only through explicit server configuration, and the in-memory dictionary remains available through explicit stub mode.

## 2. Deployment topology

```text
User's web browser                                 Developer's computer / local Python runtime
┌───────────────────────────────┐                 ┌────────────────────────────────────────────────────┐
│ Recipe Roulette HTML/CSS/JS   │  HTTP localhost │ Flask application: app.py (127.0.0.1:5000)       │
│ GET /                         │◄───────────────►│ user_interface/routes.py and templates/static     │
│ POST /api/v1/recipes (JSON)   │                 │             │                                      │
└───────────────────────────────┘                 │             ▼                                      │
                                                │ recipe_service.py                                │
                                                │ validation → ownership → submission → costs      │
                                                │             │                                      │
                                                │             ▼                                      │
                                                │ llm_api_interface (generation + pricing routing) │
                                                │       │                        │                   │
                                                │       ▼                        ▼                   │
                                                │ stub recipe lists       grocery_store_interface  │
                                                │ (default mode)          (fixture, stub, or Kroger)│
                                                │       or                  │                        │
                                                │ openai_adapter.py ── HTTPS ──► OpenAI Responses API│
                                                │                           ├──► local HTML fixture │
                                                │                           └──HTTPS► Kroger API     │
                                                └────────────────────────────────────────────────────┘
```

**Important:** The default HTML mode reads project-owned local fixture pages only. Their product names and prices are illustrative test data; no grocery website is contacted. Explicit `kroger` mode makes server-side HTTPS calls to Kroger's documented Products API; it is not HTML scraping. `html_live` remains disabled. The explicit dictionary stub also makes no grocery network requests. There is no deployed database, message broker, container orchestration, or cloud hosting configuration in the provided repository. Optional OpenAI and Kroger connections originate from the Python server, not the browser.

### 2.1 Current execution locations

| Element | Where it executes | Repo location | Deployment status |
| --- | --- | --- | --- |
| Browser interface | User's browser, served by local Flask | `user_interface/templates/index.html`; `user_interface/static/` | Implemented |
| HTTP server and routes | Local Python 3.12 process on `127.0.0.1:5000` | `app.py`; `user_interface/routes.py` | Implemented, development deployment |
| Request validation, normalization, ownership, costing | Same Python process; function calls | `recipe_service.py` | Implemented |
| Recipe-generation boundary | Same Python process; routes to stub or hosted provider | `llm_api_interface/__init__.py` | Implemented; default stub |
| Local recipe-generation stub | Same Python process | `llm_api_interface/__init__.py` | Implemented, deterministic examples |
| OpenAI model adapter | Same Python process; outbound HTTPS when enabled | `llm_api_interface/openai_adapter.py` | Implemented as optional integration; live operation not established by offline tests |
| Hosted model provider | External service operated by OpenAI | Not deployed by project | Used only in `openai` mode |
| Grocery pricing boundary | Same Python process; local HTML fixture parsing by default, explicit in-memory stub, or explicitly configured Kroger API | `grocery_store_interface/`; `retrieval.py`, `html_parser.py`, `product_extraction.py`, `product_matching.py`, `kroger_api.py` | Fixture/stub are offline; Kroger is an optional live API integration |
| Console walking skeleton | Developer's local terminal | `app.py --cli`; `user_interface/__init__.py` | Retained for Chapter 2 demonstration |
| Customer service | No executable workflow | `customer_service_interface/__init__.py` | Placeholder only |
| Login and saved recipe storage | Not deployed | No implemented persistent/authentication service | Unimplemented |
| Automated tests | Developer environment or GitHub Actions runner | `tests/`; `.github/workflows/tests.yml` | Configured; actual run status must be checked independently |

## 3. Component responsibilities and Innoslate allocation

The latest Innoslate decomposition of **C.2.4 Submit Recipe and Pricing Requests Subsystem** has four component functions. The Python workflow implements corresponding named operations, although all four execute within the same `recipe_service.py` module rather than as independently deployed services.

| Innoslate function / component | Corresponding implementation | Role |
| --- | --- | --- |
| F.2.4.1 / C.2.4.1 — Prepare Recipe Request | `prepare_recipe_request()` | Trim and normalize the ingredients, budget, and dietary restrictions passed into the preparation stage |
| F.2.4.2 / C.2.4.2 — Format and Validate API Request | `format_and_validate_api_request()` | Enforce valid top-level JSON object and field types/presence; prepare normalized request |
| F.2.4.3 / C.2.4.3 — Specify Already-Owned Recipe Ingredients | `specify_already_owned_recipe_ingredients()` | Normalize/deduplicate user-owned ingredient names for later matching |
| F.2.4.4 / C.2.4.4 — Submit Recipe and Pricing Requests | `submit_recipe_and_pricing_requests()` | Invoke recipe-generation and pricing boundaries, then assemble costed results |

**Implementation detail:** The HTTP route calls validation first; `format_and_validate_api_request()` then calls `prepare_recipe_request()` internally. Ownership processing and request submission follow. The conceptual functional decomposition should therefore not be mistaken for four standalone network services or a strictly separate chronological call sequence.

`calculate_recipe_costs()` and `identify_owned_recipe_ingredients()` also support the workflow. The repository's traceability notes identify the cost-calculation behavior as not yet separately allocated to a modeled function. Resolve that gap through model review, not by inventing an asset solely for this document.

## 4. Interfaces and data flows

### 4.1 Browser ↔ application server

- `GET /` returns the UI and static assets.
- The browser collects `ingredients` (`list[str]`, at least one), `budget` (finite positive USD number), and `dietary_restrictions` (`list[str]`, possibly empty).
- `POST /api/v2/recipes` sends these values in an `application/json` request body to Flask at the same origin. The compatible v1 endpoint remains at `/api/v1/recipes`; API definitions are in `contracts/api-v1.yaml` and `contracts/api-v2.yaml`.
- On success, v1 returns its unchanged recipe-use fields. V2 retains those fields and adds per-ingredient package provenance, `additional_package_purchase_cost`, `within_package_budget`, and package-availability status.
- On malformed/invalid input, the API returns HTTP 400 with `invalid_request` and field details. Provider and server failures return safe `backend_failure` responses with appropriate error status (see API contract).
- Browser JavaScript renders the returned recipe and cost information. It does not talk directly to OpenAI or the grocery pricing module.

### 4.2 Application server → recipe-generation interface

The route calls `format_and_validate_api_request()`, then `specify_already_owned_recipe_ingredients()`, and finally `submit_recipe_and_pricing_requests()`. The submission function calls `llm_api_interface.send_recipe_requirements(ingredients, budget, dietary_restrictions)`.

- **Stub mode (default):** In-process deterministic recipe records are returned; no external LLM request occurs. These recipes do **not** demonstrate adherence to dietary preferences.
- **OpenAI mode:** The server-side `openai_adapter.generate_recipes()` sends the submitted ingredients, budget, and restrictions to the OpenAI Responses API over HTTPS. The desired model output contains recipe names and ingredient names with quantities and supported units. Pricing is not produced by the model.
- The model adapter validates parsed responses and raises controlled errors on missing access, invalid responses, non-retryable service errors, or exhausted retries. Transient failures use bounded retries of **up to ten total attempts**, with a configurable per-attempt timeout (default 30 seconds).

### 4.3 Recipe-generation interface → grocery pricing boundary

`llm_api_interface.request_pricing()` deduplicates quantity-bearing ingredient requirements and calls `grocery_store_interface.get_ingredient_pricing()`.

- **Default data source:** Saved local HTML fixture pages; product attributes and illustrative fixture prices are extracted per request without external HTTP.
- **Offline mode:** `GROCERY_PRICING_MODE=stub` uses the historical fixed dictionary and `$1.00` unknown-name fallback. Stub values are visibly identified as demo data.
- Fixture product matches must contain the requested ingredient phrase and expose a compatible package size/unit. Package values are normalized to generated recipe quantities; unsupported or ambiguous matches fail instead of silently using an unrelated price.
- Returned product prices are treated as USD. Weight-sold items are rejected unless package-price semantics are unambiguous; incompatible or missing units are unavailable rather than converted using assumed food densities.
- The service prices every recipe ingredient, including owned ingredients, to preserve `estimated_total_cost`; ownership only excludes that normalized cost from `additional_purchase_cost`. The fixture retriever uses local files only. Budget and dietary restrictions are not included in product matching.
- Product data is not persisted or cached. HTTP requests are paced at one-second intervals, and each recipe request is limited to 25 distinct product searches.
- Normalized prices are attached to each recipe before `recipe_service.py` calculates full and additional-purchase costs.

### 4.4 Computation and return to the user

Owned-ingredient matching uses normalized, case-insensitive **exact name** comparison; it assumes enough of an owned ingredient is available. Internal generated recipes now include an amount and unit so package prices can be normalized. The service calculates:

- `estimated_total_cost`: the sum of prices of all recipe ingredients, including those owned.
- `additional_purchase_cost`: the sum of prices for ingredients **not** marked as owned.
- `within_budget`: whether `additional_purchase_cost <= budget`.

These are ingredient-use amounts, not package checkout totals. API v2
separately calculates whole-package outlay for unowned ingredients and
compares that value to the same budget in `within_package_budget`. Package
totals are per recipe because recommendations are alternatives, not one
combined cart. Missing package quotes are reported as unavailable; they are
never replaced with fabricated values.

This behavior should not be confused with the modeled stakeholder criterion comparing **full estimated cost** to budget plus a 5% allowance. That difference needs an explicit decision and traceability/deviation record.

## 5. Runtime configuration and start-up

**Prerequisites:** Python 3.12, a virtual environment, and packages in `requirements.txt` (Flask, OpenAI SDK, pytest). The current setup is local/development only, not an approved public production hosting topology.

From the repository root on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app
```

Open `http://127.0.0.1:5000`. To run the retained console demonstration instead, use `python -m app --cli`.

### 5.1 Environment variables

| Variable | Default / required | Purpose |
| --- | --- | --- |
| `RECIPE_GENERATION_MODE` | `stub` | `stub` for deterministic local recipes; `openai` for hosted generation |
| `OPENAI_API_KEY` | Required only for `openai` mode | Private server-side credential for OpenAI |
| `OPENAI_MODEL` | Repository default: `gpt-6-luna` | Configurable provider model identifier; confirm actual availability in the selected account |
| `OPENAI_TIMEOUT_SECONDS` | `30` | Per-attempt timeout; must be greater than 0 and at most 120 seconds |
| `GROCERY_PRICING_MODE` | `html_fixture` | Select `html_fixture`, live `kroger`, explicit offline `stub`, or fail-closed `html_live` |
| `KROGER_CLIENT_ID` | Required for `kroger` | Registered Kroger application client ID |
| `KROGER_CLIENT_SECRET` | Required for `kroger` | Server-side Kroger application secret |
| `KROGER_LOCATION_ID` | Required for `kroger` | Eight-character store location used to obtain price and availability |
| `GROCERY_PRICING_TIMEOUT_SECONDS` | `10` | Per-request timeout; accepted range is greater than 0 and at most 60 seconds |

Example of enabling hosted recipe generation, with a **provider-supported model ID** chosen by the team:

```powershell
$env:RECIPE_GENERATION_MODE = "openai"
$env:OPENAI_API_KEY = "<server-side-key>"
$env:OPENAI_MODEL = "<available-model-id>"
python -m app
```

The repository does not automatically read `.env` files. Keep secrets out of Git and browser code. The configured local Flask server binds to loopback; deployment to a public server requires a separate production-server, secret-management, transport-security, access-control, and logging plan. No such production topology is demonstrated by the current repository.

## 6. Failure behavior and operational constraints

| Failure or constraint | Implemented response / limitation |
| --- | --- |
| Missing or malformed required client fields | HTTP 400, structured field errors; no generation request sent |
| Missing OpenAI key or invalid provider mode | Safe configuration/service error (HTTP 503) |
| Transient provider timeout, connection error, or selected HTTP statuses | Adapter retries with bounded backoff, at most 10 total attempts |
| Invalid or unusable model output | Rejects model output and returns safe error (normally HTTP 502); does not treat it as valid recipe data |
| `html_live` requested | HTTP 503 with a safe disabled-source message; no HTTP request is made |
| Kroger credentials/location missing or invalid | HTTP 503 with safe configuration details; no fixture or stub fallback |
| Kroger HTTP 429 or timeout | Safe HTTP 503; no automatic retry amplification |
| Kroger response malformed or incomplete | Safe HTTP 502/503; no invented price or partial recipe total |
| Fixture file missing or unreadable | HTTP 503 with a safe local-source error |
| HTML structure missing/changed, product missing/ambiguous, price malformed, or package unit incompatible | HTTP 502/503 backend failure; no price is invented and no partial recipe totals are returned |
| Explicit demo pricing | `GROCERY_PRICING_MODE=stub`; deterministic prices and `$1.00` unknown fallback, disclosed as demo data |
| Dietary and allergen safety | Prompts consider restrictions, but no independently validated guarantee of dietary/allergen compliance |
| Personal accounts / persistence | Login in the console scenario is a simulation; no real authentication, saved recipe database, or user-history service |
| Availability / scalability | No production load balancer, hosted deployment, persistence, or uptime measurement documented |
| Request duration | Fixture timings exclude retailer HTTP latency; Kroger mode measures API calls, not literal webpage/S.1 scraping latency |
| Data privacy | In hosted mode, ingredients, budget, and dietary restrictions leave the local process for the configured provider; only use approved data |

## 7. Verification and deployment evidence

- API contract: `contracts/api-v1.yaml`.
- Behavior and API tests: `tests/test_functional_requirements.py`.
- OpenAI adapter tests with simulated provider responses: `tests/test_openai_integration.py`.
- HTML fixture extraction, matching, package-cost, and failure tests: `tests/test_html_pricing.py`.
- Kroger adapter and failure tests with mocked HTTP responses: `tests/test_kroger_pricing.py`.
- CI workflow: `.github/workflows/tests.yml`, using Python 3.12 and `RECIPE_GENERATION_MODE=stub`.
- Mapping and unresolved model relationships: `docs/traceability.md`.
- Needs, acceptance criteria, and contracts: repository-root `SPEC.md` (the separately prepared replacement must be committed to supersede the snapshot's placeholder).

Run verification locally:

```powershell
python -m pytest
```

**Evidence limit:** File presence and test configuration do not establish a passing test run or a successful live provider deployment. HTML fixture tests make no network calls; Kroger and OpenAI calls are mocked. No live Kroger or paid OpenAI call was made during this implementation. Preserve test results, test date, and environmental configuration as separate evidence. Never include credentials in that record.

## 8. Chapter 8–9 model/code reconciliation and open decisions

| Topic | Current state | Required team decision / follow-up |
| --- | --- | --- |
| Grocery source architecture (Chapter 11) | Local HTML fixtures exercise parsing; explicit dictionary stub remains; Kroger Products API is the opt-in live source | Team selected the official Kroger Products API as an S.1 source substitution. Update the Innoslate S.1 actors/actions and the swing-weight rationale; do not describe API latency as literal webpage scraping |
| Grocery data access | Per-request location-filtered Kroger product searches; no product catalog persistence | Review current acceptable-use rules and quotas; preserve per-request lookup, avoid cross-retailer comparison/systematic harvesting, and keep the location ID server-side |
| Ingredient quantity semantics | Internal generated recipes include quantities/units; package price is normalized only for compatible units | Serving count is still absent; quantities are for one generated recipe batch, and unavailable conversions fail visibly |
| Database and data contract (Chapter 8) | No persistent data layer | Determine whether project requirements demand a database by Chapter 8; document chosen schema and actual implementation/status |
| Model interface details | Local module calls plus optional HTTPS call | Confirm physical I² conduits and transferred I/O entities describe these boundaries consistently |
| C.2.4.3 naming | Current component asset label differs from the function's ownership/deduplication description | Reconcile asset name, function, and actual behavior in Innoslate |
| Cost-calculation allocation | Service-level helper outside direct allocation shown in traceability notes | Decide and document where the behavior belongs in the physical architecture |
| Budget interpretation | Current `within_budget` uses additional-purchase cost | Reconcile with the modeled full-cost / 5%-allowance requirement |
| Retry semantics | At most 10 **total attempts** in code | Reconcile with modeled “up to 10 retry attempts” wording |
| Component specification (Chapter 9) | Component functions exist in code | Select one fully specified second-level component; provide model-derived requirements, ICOM details, and verification criteria |
| Chapter 9 deviation evidence | No completed deviation log in supplied repository snapshot | Run the prescribed one-pass implementation exercise, record deviations in `docs/deviation-log.md`, and document disposition; do not retroactively represent earlier code as a new one-pass build |
| Production deployment | Loopback development server only | Define and approve hosting, authentication, HTTPS, monitoring, and operational controls if required later |

## 9. Summary

Recipe Roulette currently operates as a locally hosted **Flask monolith with modular in-process components**. The browser communicates with the Flask HTTP API, the application validates and processes requests, a recipe-generation boundary uses deterministic recipes or an optional hosted OpenAI model, and a separate grocery-pricing boundary defaults to local HTML fixtures. The official Kroger Products API is an explicit live mode and a source-interface substitution for S.1; it is not literal HTML scraping. The in-memory dictionary remains an explicit stub. The architecture model and component specifications remain the controlling source for outstanding design, traceability, and verification decisions.
