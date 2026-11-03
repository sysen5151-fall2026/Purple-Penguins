# Route Table

The Flask homepage collects recipe preferences and displays results returned by the existing deterministic API, including ingredient ownership and additional-purchase estimates.

| Method | Path | Purpose | Planned behavior | Related F.2 functions | Status |
|---|---|---|---|---|---|
| GET | `/` | Load the Recipe Roulette browser interface | Render already-owned ingredients, budget, and optional dietary-restriction controls; explain the simulated login prerequisite and demonstration-data limits; display returned ingredient ownership, full recipe cost, additional purchase cost, and budget status. | F.2.2, F.2.3, F.2.7 | Implemented — browser UI |
| POST | `/api/v1/recipes` | Submit preferences and generate recipe results | Validate and normalize the existing JSON request, prepare a normalized/deduplicated ownership context before submission, call the separate deterministic recipe and pricing stubs, and return full cost, additional purchase cost, ownership, and budget comparison while preserving legacy response fields. | F.2.4; verified subfunctions F.2.4.1–F.2.4.4; additional-cost calculation has no separate modeled function | Implemented — deterministic stub integration |

The “Spin for Recipes” action posts the form values to `/api/v1/recipes`. F.2.4.3 specifies a normalized, deduplicated internal ownership list before F.2.4.4 submits the recipe and pricing requests. Recipe generation and pricing remain separate deterministic stub calls; backend response assembly identifies ingredient ownership and calculates cost fields. XML10 has no separate modeled cost-calculation function, so `calculate_recipe_costs` is an unallocated service-level helper. The browser renders backend values without filtering recipes or recalculating costs.

The initial route set intentionally excludes login, customer support, saved recipes, recipe-detail, and shopping-list endpoints. Those routes should be considered only when F.2.1, F.2.5, F.2.6, or F.2.8 is scheduled and its behavior is confirmed.

F.2.2 has a modeled **Login Approved** input from F.2.1. The page identifies this prerequisite as simulated demo mode; no authentication is performed.
