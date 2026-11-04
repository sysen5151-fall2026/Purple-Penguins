# Phase 6 — Live LLM API Integration

Replace the deterministic recipe-generation stub with optional live OpenAI recipe generation through the existing Python `llm_api_interface`. Keep deterministic stub mode as the default. Do not call the external API from browser JavaScript or expose credentials.

Send the user's existing ingredients, budget, and dietary restrictions to the provider. Require structured recipe output containing recipe names and ingredient names only; validate it locally and convert it to the existing application structures. Do not ask the model for prices. Preserve Phase 5 ownership matching, additional-purchase calculation, budget comparison, existing API request and success schemas, browser flow, and Chapter 2 console workflow.

Keep grocery pricing deterministic. Handle missing credentials, authorization errors, timeouts, transient provider failures, and malformed responses safely. Mock provider responses in automated tests; do not make paid API calls in tests. Use no more than ten total attempts for transient failures (initial request plus up to nine retries), and disable SDK-internal retries so the limit is explicit.

Document that live mode sends user preferences to OpenAI, recipes and prices are not guaranteed, login remains simulated, and pricing remains demonstration data. Update traceability using verified XML10 identifiers only. Document the XML10 LLM/web-search pricing discrepancy as a deviation and request a later model update. Do not add a cache, persistent recommendation reuse, or application-wide spend enforcement; mark the approved model requirements as deferred. Do not commit or push.

## Approved implementation decisions

- `RECIPE_GENERATION_MODE=stub|openai`; default to `stub`.
- Read `OPENAI_API_KEY` from the server environment only.
- Keep pricing in the existing deterministic grocery-store interface.
- Defer caching and application-level spend enforcement; record model requirements as pending.
- Retry transient failures only, with at most ten total attempts.
- Preserve the existing request and successful response schemas.
