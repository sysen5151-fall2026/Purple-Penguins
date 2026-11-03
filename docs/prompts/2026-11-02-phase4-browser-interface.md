# Prompt summary — Phase 4 browser interface integration

Implement the approved Phase 4 Recipe Roulette browser interface by extending the existing Flask homepage and using the existing `POST /api/v1/recipes` endpoint.

## Required behavior

- Let the user enter one or more ingredients, a positive budget in USD, and optional dietary restrictions.
- Split ingredient and restriction entries into the API's string arrays and submit the existing JSON request schema with JavaScript `fetch`.
- Show loading state, prevent duplicate submissions, validate user inputs, handle contract validation errors and network/server failures, and display an empty-results state.
- Render the returned recipes, ingredients, estimated ingredient prices, and estimated totals faithfully. Do not filter or alter returned recipes based on submitted preferences.
- Preserve Recipe Roulette branding and responsive styling.

## Architecture and limitations

- Reuse the existing Flask routes, API contract, deterministic recipe-generation stub, deterministic pricing stub, and Chapter 2 console walking skeleton.
- Do not modify the API schemas or backend recipe/pricing logic.
- Do not add live external services, authentication, databases, shopping-list editing, customer service, or a frontend framework.
- Clearly identify the fixed recipes and prices as demonstration data; do not claim personalization, budget compliance, or dietary safety.
- The F.2.1 Login Approved prerequisite for F.2.2 may be represented as simulated demo mode only. Do not collect credentials, implement authentication, or imply authentication occurred.
- Use verified function and component IDs from the latest export, `Recipe Roulette (8).xml`; do not invent requirement IDs.

## Tests and documentation

- Add focused tests for homepage controls, demonstration notices, and static asset delivery while preserving API and console compatibility.
- Update traceability, route-table, and prompt-log documentation. Distinguish automated checks from manual browser verification and leave unknown reviewer/model details for manual confirmation.
- Run `python -m pytest -q` and `git diff --check`; confirm Flask startup and provide exact browser testing instructions.
- Do not commit or push.
