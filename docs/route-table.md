# Route Table

The Flask homepage collects owned ingredients, ZIP code, store, budget, and dietary restrictions. Recipe generation defaults to deterministic local recipes; OpenAI mode can also return unverified store/ZIP-contextualized price estimates. The app does not connect to retailer pricing systems.

| Method | Path | Purpose | Planned behavior | Related F.2 functions | Status |
|---|---|---|---|---|---|
| GET | `/` | Load the Recipe Roulette browser interface | Render owned ingredients, ZIP input, store dropdown, budget, and optional dietary restrictions; explain the simulated login prerequisite; disclose whether OpenAI price estimates will be used. | F.2.2, F.2.3, F.2.7 | Implemented — browser UI |
| POST | `/api/v1/recipes` | Submit preferences and generate recipe results | Validate the request, prepare ownership context, generate recipes through the configured stub or OpenAI adapter, then use fixed demo prices or (in OpenAI mode with store and ZIP) a separate unverified OpenAI price-estimation request. The successful response shape is unchanged. Provider failures use safe `502`/`503` responses; validation remains `400`. | F.2.4; verified subfunctions F.2.4.1–F.2.4.4; transient recipe retries are F.2.5; cost calculation has no separate modeled function | Implemented — stub default; optional OpenAI mode |

The “Spin for Recipes” action posts the form values to `/api/v1/recipes`. F.2.4.3 specifies a normalized, deduplicated internal ownership list before F.2.4.4 submits the recipe request. The recipe-generation adapter returns validated recipe names and ingredient names. In OpenAI mode, the pricing estimator receives generated ingredient names and, when supplied, store/ZIP context; estimates are not verified against retailer data. Stub mode continues to use the local dictionary. Backend response assembly identifies ownership and calculates cost fields. XML10 has no separate modeled cost-calculation function, so `calculate_recipe_costs` remains an unallocated service-level helper. The browser displays backend values without filtering recipes or recalculating costs.

OpenAI mode requires server-side `OPENAI_API_KEY` configuration. The request contract and successful response fields are unchanged. Transient connection, timeout, rate-limit, and server failures are retried up to ten total attempts; missing credentials, authorization failures, malformed structured output, and other non-transient errors are not retried. No API key is returned to the browser.

The initial route set intentionally excludes login, customer support, saved recipes, recipe-detail, and shopping-list endpoints. Those routes should be considered only when F.2.1, F.2.5, F.2.6, or F.2.8 is scheduled and its behavior is confirmed.

F.2.2 has a modeled **Login Approved** input from F.2.1. The page identifies this prerequisite as simulated demo mode; no authentication is performed.
