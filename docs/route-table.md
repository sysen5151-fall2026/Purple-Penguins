# Route Table

The Flask foundation currently implements only the dashboard shell. The recipe-generation workflow remains planned.

| Method | Path | Purpose | Planned behavior | Related F.2 functions | Status |
|---|---|---|---|---|---|
| GET | `/` | Load the Recipe Roulette homepage | Return a basic branded page stating that the web interface is under development. It does not collect preferences or display recipe results. | F.2 foundation only; F.2.2, F.2.3, and F.2.7 are not implemented | Implemented — foundation only |
| POST | `/api/v1/recipes` | Submit preferences and generate recipe results | Validate and normalize the JSON request, call the existing deterministic recipe and pricing stubs, and return recipe ingredients and estimated costs. | F.2.4; Phase 3 subfunctions F.2.4.1–F.2.4.3 | Implemented — deterministic stub integration |

The homepage remains a foundation page and does not yet provide the “Spin for Recipes” interaction. The API can be exercised directly; the dashboard workflow is still planned.

The initial route set intentionally excludes login, customer support, saved recipes, recipe-detail, and shopping-list endpoints. Those routes should be considered only when F.2.1, F.2.5, F.2.6, or F.2.8 is scheduled and its behavior is confirmed.

F.2.2 has a modeled **Login Approved** input from F.2.1. The proposed local demo-mode behavior is documented in `docs/traceability.md`; this route table does not imply that login or demo mode is implemented.
