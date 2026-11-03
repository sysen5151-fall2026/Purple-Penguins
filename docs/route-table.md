# Route Table

The Flask homepage now collects recipe preferences and displays results returned by the existing deterministic API.

| Method | Path | Purpose | Planned behavior | Related F.2 functions | Status |
|---|---|---|---|---|---|
| GET | `/` | Load the Recipe Roulette browser interface | Render ingredient, budget, and optional dietary-restriction controls; explain the simulated login prerequisite and fixed demonstration data; display loading, error, empty-results, and returned recipe/pricing states. | F.2.2, F.2.3, F.2.7 | Implemented — browser UI |
| POST | `/api/v1/recipes` | Submit preferences and generate recipe results | Validate and normalize the JSON request, call the existing deterministic recipe and pricing stubs, and return recipe ingredients and estimated costs. | F.2.4; Phase 3 subfunctions F.2.4.1–F.2.4.3 | Implemented — deterministic stub integration |

The “Spin for Recipes” action posts the form values to `/api/v1/recipes`. Recipe generation and pricing remain in the existing backend service and deterministic stubs; the browser renders the API response without filtering it.

The initial route set intentionally excludes login, customer support, saved recipes, recipe-detail, and shopping-list endpoints. Those routes should be considered only when F.2.1, F.2.5, F.2.6, or F.2.8 is scheduled and its behavior is confirmed.

F.2.2 has a modeled **Login Approved** input from F.2.1. The page identifies this prerequisite as simulated demo mode; no authentication is performed.
