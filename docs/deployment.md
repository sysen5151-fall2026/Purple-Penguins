# Recipe Roulette — Component and Deployment View

**Project:** SYSEN 5151 — Recipe Roulette  
**Deliverable:** Chapter 8, `docs/deployment.md` (maintained through Chapter 9)  
**Basis:** `Purple-Penguins-Phase_5_M2` repository snapshot and Recipe Roulette Innoslate architecture export (November 2026)  
**Status:** **Documented implementation**, not evidence of production deployment or verified live external services.

## 1. Purpose and system boundary

This document describes **what runs where and what communicates with what** for the current Recipe Roulette product build. It distinguishes implemented processes, in-process modules, locally simulated external systems, and the optional hosted LLM service. It also records where the implementation still differs from the system architecture and Chapter 8–9 objectives.

The system of interest is the Recipe Roulette application. A user supplies available ingredients, a budget (USD), and dietary restrictions; the application requests recipe candidates, obtains estimated ingredient prices, identifies ingredients the user already owns, computes purchase costs, and presents results. The external Grocery Store and LLM API appear in the system context, but their **deployment status differs**: grocery pricing is presently a local stub, and the LLM is simulated by default or hosted when explicitly configured.

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
                                                │ (default mode)          (fixed price dictionary) │
                                                │       or                                           │
                                                │ openai_adapter.py ───── HTTPS ────────────────────┼──► OpenAI Responses API
                                                └────────────────────────────────────────────────────┘
```

**Important:** The `grocery_store_interface` name reflects the modeled system boundary, **not** a deployed grocery service or real store integration. There is no deployed database, message broker, container orchestration, or cloud hosting configuration in the provided repository. The optional external LLM connection is made directly by the local Python server, not by the browser.

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
| Grocery pricing boundary | Same Python process with fixed in-memory prices | `grocery_store_interface/__init__.py` | **Stub, not real data retrieval** |
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
- `POST /api/v1/recipes` sends these values in an `application/json` request body to Flask at the same origin. Full API definitions live in `contracts/api-v1.yaml`.
- On success, Flask returns HTTP 200 with `recipes`, each with a name, priced ingredients, ownership flags, `estimated_total_cost`, `additional_purchase_cost`, and `within_budget`.
- On malformed/invalid input, the API returns HTTP 400 with `invalid_request` and field details. Provider and server failures return safe `backend_failure` responses with appropriate error status (see API contract).
- Browser JavaScript renders the returned recipe and cost information. It does not talk directly to OpenAI or the grocery pricing module.

### 4.2 Application server → recipe-generation interface

The route calls `format_and_validate_api_request()`, then `specify_already_owned_recipe_ingredients()`, and finally `submit_recipe_and_pricing_requests()`. The submission function calls `llm_api_interface.send_recipe_requirements(ingredients, budget, dietary_restrictions)`.

- **Stub mode (default):** In-process deterministic recipe records are returned; no external LLM request occurs. These recipes do **not** demonstrate adherence to dietary preferences.
- **OpenAI mode:** The server-side `openai_adapter.generate_recipes()` sends the submitted ingredients, budget, and restrictions to the OpenAI Responses API over HTTPS. The desired model output is a JSON object containing `recipes`, an array of objects containing only `name` and an `ingredients` string array. Pricing is not produced by the model.
- The model adapter validates parsed responses and raises controlled errors on missing access, invalid responses, non-retryable service errors, or exhausted retries. Transient failures use bounded retries of **up to ten total attempts**, with a configurable per-attempt timeout (default 30 seconds).

### 4.3 Recipe-generation interface → grocery pricing boundary

`llm_api_interface.request_pricing()` collects ingredient names from recipe candidates and calls `grocery_store_interface.get_ingredient_pricing()`.

- **Current data source:** A seven-item price dictionary embedded in code, returning USD values.
- **Unknown ingredient fallback:** `$1.00` per ingredient name. This is an approximation that can distort live-generated recipe estimates.
- **No network request is made** to a grocery store; no database or store-selection functionality is implemented.
- Returned prices are attached to each recipe before `recipe_service.py` calculates the full and additional-purchase costs.

### 4.4 Computation and return to the user

Owned-ingredient matching uses normalized, case-insensitive **exact name** comparison; it does not infer synonyms or quantities. The service calculates:

- `estimated_total_cost`: the sum of prices of all recipe ingredients, including those owned.
- `additional_purchase_cost`: the sum of prices for ingredients **not** marked as owned.
- `within_budget`: whether `additional_purchase_cost <= budget`.

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
| Grocery pricing data unavailable or unknown | No real external source to fail; unknown names silently receive `$1.00` stub price |
| Dietary and allergen safety | Prompts consider restrictions, but no independently validated guarantee of dietary/allergen compliance |
| Personal accounts / persistence | Login in the console scenario is a simulation; no real authentication, saved recipe database, or user-history service |
| Availability / scalability | No production load balancer, hosted deployment, persistence, or uptime measurement documented |
| Request duration | Live provider may take longer than a 10-second modeled response-time objective because of timeout and retries |
| Data privacy | In hosted mode, ingredients, budget, and dietary restrictions leave the local process for the configured provider; only use approved data |

## 7. Verification and deployment evidence

- API contract: `contracts/api-v1.yaml`.
- Behavior and API tests: `tests/test_functional_requirements.py`.
- OpenAI adapter tests with simulated provider responses: `tests/test_openai_integration.py`.
- CI workflow: `.github/workflows/tests.yml`, using Python 3.12 and `RECIPE_GENERATION_MODE=stub`.
- Mapping and unresolved model relationships: `docs/traceability.md`.
- Needs, acceptance criteria, and contracts: repository-root `SPEC.md` (the separately prepared replacement must be committed to supersede the snapshot's placeholder).

Run verification locally:

```powershell
python -m pytest
```

**Evidence limit:** File presence and test configuration do not establish a passing test run or a successful live OpenAI deployment. Preserve test results, selected model, test date, and environmental configuration as separate evidence. Never include credentials in that record.

## 8. Chapter 8–9 model/code reconciliation and open decisions

| Topic | Current state | Required team decision / follow-up |
| --- | --- | --- |
| Real grocery data access (Chapter 8) | Stub dictionary | Select a real provider and define source schema, refresh, currency, unit/quantity, failures, and pricing policy; or document approved scope change |
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

Recipe Roulette currently operates as a locally hosted **Flask monolith with modular in-process components**. The browser communicates with the Flask HTTP API, the application validates and processes requests, a recipe-generation boundary uses either deterministic recipes or an optional hosted OpenAI model, and a separate local pricing stub supplies estimated ingredient costs. This topology supports demonstrations and automated component/API testing; it does **not yet provide a real grocery-data adapter, persistent accounts/database, or a verified production deployment**. The architecture model and component specifications remain the controlling source for outstanding design, traceability, and verification decisions.
