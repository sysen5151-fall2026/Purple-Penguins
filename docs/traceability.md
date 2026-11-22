# F.2 Function Traceability

**Status:** F.2.2 and F.2.3 have browser-interface implementations; F.2.4.1–F.2.4.4 implement request preparation, validation, ownership context, and submission; F.2.4.4 supports deterministic recipe stub mode by default and optional OpenAI recipe generation; F.2.5 retries transient OpenAI failures; and F.2.7 displays backend results. Grocery pricing defaults to local coursework HTML fixtures, supports explicit deterministic dictionary stub mode, and has an opt-in Kroger Products API mode. Additional-purchase-cost calculation is a service-level responsibility with no separate function in the latest model. F.2.1, F.2.6, and F.2.8 remain unimplemented. F.2.2's modeled Login Approved prerequisite is visibly simulated; no authentication is performed.

## Traceability matrix

Requirement relationships are recorded only where verified in `Recipe Roulette (10).xml`. C.2.4 has direct subsystem-level links to requirements 2.7.1, 2.8.1, and 2.9.1; this does not assert that every F.2.4 subfunction has a direct link. Other unverified requirement IDs remain **Pending Verification**.

| Innoslate function ID | Exact function name | Related requirement ID | Proposed Python module/function | Planned automated test | Implementation status |
|---|---|---|---|---|---|
| F.2.1 — `I_AW2W0HS6YEH5N_9C41E7112B61C` | Request and Validate User Login | Pending Verification | `user_interface/auth.py::request_and_validate_user_login` | `test_f21_demo_login_approval_is_explicit` | Not Implemented; later phase |
| F.2.2 — `I_7XRQR0GFSTJER_B0W15Z68VZJM2` | Collect User Ingredients | Pending Verification | `user_interface/templates/index.html`; `user_interface/static/js/recipe-roulette.js` form submission | `test_homepage_contains_recipe_preference_controls_and_demo_notices` | Implemented in browser demo; F.2.1 approval is simulated |
| F.2.3 — `I_CTXZXZ70BGHV4_AFHBBP2CRP43Y` | Collect budget and Dietary Restrictions | Pending Verification | `user_interface/templates/index.html`; `user_interface/static/js/recipe-roulette.js` form submission | `test_homepage_contains_recipe_preference_controls_and_demo_notices` | Implemented in browser demo |
| F.2.4 — `I_7Y3Y133TSAG54_98MDRGWJ519M3` | Submit Recipe and Pricing Requests | F.2.4 link: Pending Verification; C.2.4 subsystem links: 2.7.1, 2.8.1, 2.9.1 | `recipe_service.py::submit_recipe_and_pricing_requests`; `llm_api_interface::send_recipe_requirements` | `test_f24_submits_requirements_to_recipe_and_pricing_stubs`; `test_live_api_keeps_phase5_pricing_and_ownership_calculation` | Implemented — deterministic recipe stub by default; optional OpenAI generation; fixture default, Kroger API opt-in, explicit dictionary stub |
| F.2.5 — `I_4RZHP3MTHRKRE_A896NKDQGJ2S4` | Resend LLM API Request | Pending Verification | `llm_api_interface/openai_adapter.py::generate_recipes` retry loop | `test_openai_retries_transient_connection_failure`; `test_openai_retries_at_most_ten_total_attempts` | Implemented for transient OpenAI failures; maximum ten total attempts |
| F.2.6 — `I_BW2QHYF5AMGMM_ATJZXVSX8MFCB` | Contact Customer Support | Pending Verification | `customer_service_interface/__init__.py::submit_support_request` | `test_f26_submits_question_and_feedback_to_customer_service` | Not Implemented; later phase |
| F.2.7 — `I_34QM2GKG6PKA5_AJ7AXJC1FBE5K` | Display Recipes and Pricing Results | Pending Verification | `user_interface/static/js/recipe-roulette.js::renderRecipes` | `test_homepage_loads_recipe_interface_assets` (asset delivery; rendering requires browser verification) | Implemented in browser; displays ownership, full cost, purchase cost, and budget status from API |
| F.2.8 — `I_6QP83SB7YMK8Z_8G41HVK3PJYRS` | Modify Shopping List | Pending Verification | `shopping_list.py::apply_modifications` | `test_f28_applies_shopping_list_modifications` | Not Implemented; later phase |

### F.2.4 subfunctions verified in XML10

The function names, global IDs, and component allocations below are verified against the latest Innoslate export, `Recipe Roulette (10).xml`. Phase 3 originally used export 8; XML10 is the current source for the revised F.2.4 hierarchy. C.2.4 has direct subsystem-level links to requirements 2.7.1, 2.8.1, and 2.9.1; direct requirement links to individual F.2.4 subfunctions remain Pending Verification.

| Innoslate function and component IDs | Related requirement ID | Implemented Python function | Automated test | Implementation status |
|---|---|---|---|---|
| F.2.4.1 — Prepare Recipe Request (`I_4FQB4AXSNMJTB_BP518PV5V30BN`); C.2.4.1 — Recipe Request Preparation Component (`I_FRJYSFT6PYHG9_AJWNE3781P3TM`) | Pending Verification | `recipe_service.py::prepare_recipe_request` | `test_recipe_endpoint_normalizes_preferences_and_passes_restrictions` | Implemented |
| F.2.4.2 — Format and Validate API Request (`I_C5HVGPQMDEKPB_822HFWSBZWGEH`); C.2.4.2 — API Request Validation Component (`I_8FYMCCF9KYGYS_829BEWYMF1P63`) | Pending Verification | `recipe_service.py::format_and_validate_api_request`; invoked by `user_interface.routes.generate_recipes` | `test_recipe_endpoint_reports_missing_required_inputs`; `test_recipe_endpoint_rejects_invalid_budget_values`; `test_recipe_endpoint_rejects_invalid_ingredients`; `test_recipe_endpoint_rejects_malformed_json` | Implemented |
| F.2.4.3 — Specify Already-Owned Recipe Ingredients (`I_C3XRN0P8R0JED_AS6RHTHBNZ0C6`); C.2.4.3 — Ingredients List Redundancy Removal Device (`I_35QN82Z6Q6JT8_9S98VJAVR325X`) | Pending Verification | `recipe_service.py::specify_already_owned_recipe_ingredients` | `test_f243_specifies_normalized_deduplicated_owned_ingredients`; `test_f243_ownership_context_is_passed_to_submission` | Implemented — prepares a normalized, deduplicated internal ownership list |
| F.2.4.4 — Submit Recipe and Pricing Requests (`I_CZFVR1YCP8J7C_87K5PYQC4ZNN0`); C.2.4.4 — Request Submission Component (`I_6FJAPA7HG2GJC_9B0D0PAPPRQJS`) | C.2.4 subsystem links: 2.7.1, 2.8.1, 2.9.1; direct subfunction links: Pending Verification | `recipe_service.py::submit_recipe_and_pricing_requests`; `llm_api_interface::send_recipe_requirements`; `llm_api_interface/openai_adapter.py::generate_recipes` | `test_f24_submits_requirements_to_recipe_and_pricing_stubs`; `test_openai_request_uses_structured_output_and_user_preferences`; `test_live_api_keeps_phase5_pricing_and_ownership_calculation` | Implemented — stub default or validated OpenAI recipe generation; fixture default, opt-in Kroger API or explicit dictionary demo pricing |

The API endpoint returns pricing to satisfy the contract. The legacy `estimated_total_cost` remains the full cost of all recipe ingredients; Phase 5 adds ownership and additional-purchase information without removing existing response fields.

Request preparation trims surrounding whitespace from ingredient and dietary-restriction strings and converts the positive numeric budget to a float. Values that become empty after trimming are rejected so a whitespace-only string is not treated as a meaningful ingredient or restriction.

F.2.4.3 prepares a case-folded, whitespace-trimmed, deduplicated ownership list before F.2.4.4 submission. Returned recipe ingredient names are matched against that list after pricing. The public request JSON shape and recipe-generation inputs remain unchanged. Internal generated recipe results now include quantities and supported units for pricing normalization.

The service-level `calculate_recipe_costs` helper calculates full and additional purchase costs after pricing. XML10 contains no separate F.2.4 cost-calculation function or ICOM flow, so this helper is documented as an unallocated implementation responsibility; no function ID is assigned. No F.2.4.5 appears in XML10. Phase 4's Python tests verify page controls and asset delivery; they do not execute browser JavaScript, so dynamic result rendering is verified separately through browser smoke testing.

## Verified ICOM and internal-flow notes

ICOM assignments below are taken from the F.2 decomposition diagram and its relationship records in the latest export, `Recipe Roulette (10).xml`. Names and global IDs are reproduced from that export.

| Function | Inputs | Controls | Outputs | Internal flow(s) |
|---|---|---|---|---|
| F.2.1 | Login Credentials — `I_9ZXZG9W4BEGYP_8ND7T3SV6CJMN` | Session Intitates — `I_F2MBDEQD6EJJ1_8MV4K41QX624H` | Request for User Login — `I_2JT79HMQ8YKD1_ASDM379JY737Q`; Approve Login — `I_17P62SC2DTJM3_A9QA5QK75YYSJ` | Login Approved — `I_CSSY5WGCB8KAK_8SFB4X6DXXQRF` → F.2.2 |
| F.2.2 | User Preferences / Ingredients — `I_ABYZTK7C68KDT_BNTJX2PYK8N1Q`; Login Approved — `I_CSSY5WGCB8KAK_8SFB4X6DXXQRF` | None shown | Ingredient Request — `I_D5DFGPJ8VAJJN_BM4J5XG2DYTZV` | User Ingredients — `I_CR10TPVM04GDG_96MANTHTT4BT5` → F.2.4 |
| F.2.3 | User Preferences / Ingredients — `I_ABYZTK7C68KDT_BNTJX2PYK8N1Q` | None shown | Request Monetary Budget — `I_2AJ58PD5A4GZB_9MQJZ47WPV7TA`; Request Dietary Restrictions — `I_180E5JZ4RJJRT_BTM39GRESR7CP` | Budget and Dietary Restrictions — `I_8RGEWPBTDAGNJ_9NETAHKBAKQY2` → F.2.4 |
| F.2.4 | User Ingredients — `I_CR10TPVM04GDG_96MANTHTT4BT5`; Budget and Dietary Restrictions — `I_8RGEWPBTDAGNJ_9NETAHKBAKQY2` | None shown | Ingredients/Budget/Dietary Restrictions — `I_1P1WPWQASTH3Q_8XCGY5SMFZFBN`; Pricing request — `I_B0DN39R3X6H81_8Z851DK8CF9D5` | Prepared Recipe Request — `I_A584M1M5QGHWD_93FC4QPSXE8M7` → F.2.4.2; Validated API Request — `I_DNCJ8KCT0EJTG_BGDAHPHJE18RQ` → F.2.4.3; Recipe Request with Ingredient Ownership Information — `I_BN6VB8CYNPJ86_ACJBRM6Y7PR95` → F.2.4.4 |
| F.2.5 | Error Response — `I_B03ZP5ME6WKT3_AHE6D9SMEKV0B` | None shown | Retry (Up to 10 Times) — `I_5XRZYESY7AJ04_8Z0E305ZDGBMH` | No retry connection back to F.2.4 is shown |
| F.2.6 | Question/Concern — `I_BZ1QS58HT6JFB_8VW9E66M7ZXAQ`; Provides Feedback — `I_A8JHHDBJC4J1J_9T2XMH65HZB3W` | None shown | Customer Service Request — `I_C7BZA7A5C0GZA_8JQEEBH9NMCJG`; Support Response — `I_EF1JXBMVAYKB7_BP49GDVAMEECN` | Customer-service exchange is outside the F.2 internal sequence |
| F.2.7 | Recipe List — `I_EQTZM8DX3PJF1_AJY5R8W63XB38`; Recipe Pricing Data — `I_9HEE57NZFGJHX_BM6CG7SDTCHVQ` | None shown | Recipe & pricing results — `I_8594E5V832H36_B7P4W47Y6MSQZ` | Receives recipe and pricing data from outside the F.2 boundary |
| F.2.8 | Recipe List — `I_EQTZM8DX3PJF1_AJY5R8W63XB38`; Recipe Pricing Data — `I_9HEE57NZFGJHX_BM6CG7SDTCHVQ` | Shopping List Modifications — `I_FPJP7SJGVAJQK_AEY9M1QK1EQ7E` | Display Modifications — `I_AJ20ZNFZ9TGSC_8QXNXKZJYEVT1` | No connection to another F.2 function is shown |

## Phase 4 browser workflow mapping

| Function | Function global ID | Physical mechanism | Mechanism global ID | Browser implementation | Requirement ID |
|---|---|---|---|---|---|
| F.2.2 — Collect User Ingredients | `I_7XRQR0GFSTJER_B0W15Z68VZJM2` | C.2.2 — Collect User Ingredients Subsystem | `I_FCDN2YG3F6JZ2_AMZ9CZJHY2C5Y` | Ingredient entry in the preference form; values are split into the API's string array | Pending Verification |
| F.2.3 — Collect budget and Dietary Restrictions | `I_CTXZXZ70BGHV4_AFHBBP2CRP43Y` | C.2.3 — Collect Budget and Dietary Restrictions Subsystem | `I_CHM3F1BTT6G0Q_B5R9H37QCEE57` | Positive USD budget and optional restrictions are submitted through the same form | Pending Verification |
| F.2.4 — Submit Recipe and Pricing Requests | `I_7Y3Y133TSAG54_98MDRGWJ519M3` | C.2.4 — Submit Recipe and Pricing Requests Subsystem | `I_C6YMRGVVSEGHA_82M4PD6H48YHR` | Existing `POST /api/v1/recipes` API; stub default or OpenAI recipe-generation adapter; local HTML fixture pricing and explicit dictionary stub | C.2.4 links to 2.7.1, 2.8.1, and 2.9.1 |
| F.2.7 — Display Recipes and Pricing Results | `I_34QM2GKG6PKA5_AJ7AXJC1FBE5K` | C.2.7 — Display Recipes and Pricing Results Subsystem | `I_96E93MMBC6H8V_A7890DCT74CN3` | JavaScript renders ownership, full recipe cost, additional purchase cost, and backend budget status without filtering recipes | Pending Verification |

## F.2.2 login dependency and demonstration mode

F.2.2 has a modeled **Login Approved** input from F.2.1 (`I_CSSY5WGCB8KAK_8SFB4X6DXXQRF`). Phase 4 displays that prerequisite as simulated demo mode so the browser workflow can run without implementing authentication.

**Demonstration limitation:** The page states that login approval is simulated. It collects no credentials, creates no authenticated session, and does not change the Innoslate dependency.

## Phase 5 ingredient-aware pricing and model gap

The approved Phase 5 behavior uses the existing `ingredients` request array as the user's already-owned ingredient list. The service preserves normalized exact-name matching and adds only a controlled compatibility rule for standard dry-pasta names and shapes; other variety/form differences remain unconfirmed. It keeps each full estimated price, calculates the full recipe cost and additional purchase cost, and compares only the additional purchase cost with the submitted budget. The browser displays these backend-calculated fields and does not calculate deductions.

XML10 confirms F.2.4.3 — Specify Already-Owned Recipe Ingredients and F.2.4.4 — Submit Recipe and Pricing Requests, along with their C.2.4.3 and C.2.4.4 component allocations. It contains no F.2.4.5 and no separate cost-calculation function or associated flow. Accordingly, `recipe_service.py::calculate_recipe_costs` remains a service-level helper with no assigned Innoslate function ID. The feature adds no request field: the existing `ingredients` array is interpreted as items already owned. Requirement IDs remain Pending Verification where no direct relationship is available at the function or subfunction level.

## Phase 6 OpenAI integration and model alignment

| Modeled entity | Verified identifier / relationship | Implementation mapping | Status |
|---|---|---|---|
| STH.1.1.13 — Integrate with OpenAI API | `I_5YHKDR6XGJGTZ_8M5RX6SJDDT9G` | `llm_api_interface/openai_adapter.py::generate_recipes` | Implemented; server-side OpenAI SDK call |
| App-to-LLM-API interface | `I_69ZMMS1CW6HYJ_BNGEQF7N27XNQ` | `llm_api_interface::send_recipe_requirements` → OpenAI adapter | Implemented; API key is not passed to the browser |
| C.3 — LLM API | `I_3WCQRRY44RKSN_9VWB661K6RNYT` | OpenAI adapter for recipe names and ingredient lists | Implemented in optional OpenAI mode |
| 2.4.1.1 — JSON Request Formatting | `I_FK80M2PJNGH7G_9JXQNNAEBM51E` | Strict JSON Schema request plus local response validation | Implemented |
| 2.8.1 — LLM Submission Failure Status | `I_AZQ74Q8CA4KDK_8M3JA62TXSRRE` | Typed provider errors mapped to safe `502`/`503` API responses | Implemented |
| 2.9.1 — Failed Request Handoff | `I_EGY6YESYFGGP3_AYR3SBZZKA7V0` | Route returns contract-shaped backend failure; internal details are logged server-side | Implemented |
| C.2.4 subsystem requirement links | 2.7.1, 2.8.1, 2.9.1 | Request submission, response, and failure handling | Verified at C.2.4 subsystem level; subfunction-specific links are not inferred |
| Sys.2.1.1 — Cost Control | `I_1K41R2P6NGJ4F_9849VSGK2C32K` | No cumulative spend limit or request-cost ledger | Deferred; Pending Implementation |
| Sys.2.1.2 — Recommendation Reuse | `I_2YMHVNRGN2GM1_86SE86A10JNKK` | No cache or persisted recommendation reuse | Deferred; Pending Implementation |
| Duplicate API Request Prevention | Requirement/global ID not verified | Browser disables the submit button while a request is in flight; no cross-request idempotency store | Partial only; implementation and requirement identity Pending Verification |

The v1 request shape and successful response schema are unchanged. OpenAI receives only the user's ingredients, budget, and dietary restrictions and returns recipe names plus ingredient requirements with names, quantities, and supported units. It is instructed to include required varieties/forms without inventing brands; pricing uses the generated names as Kroger search terms. Ownership matching remains separate from product search. The response is locally validated before it reaches the independent pricing boundary. Current Chapter 11 default pricing reads local coursework HTML fixtures; the opt-in Kroger mode uses the location-filtered Products API. The model's pricing request is not used to obtain production prices.

Live mode requires `OPENAI_API_KEY` on the server. Missing credentials and authorization errors are reported as safe `503` failures; invalid provider data maps to `502`; transient connection, timeout, rate-limit, and server errors are retried with a maximum of ten total attempts (the initial attempt plus at most nine retries). The SDK's automatic retries are disabled so the application owns this bound. This implements F.2.5 for transient provider errors but the XML10 diagram does not show a retry flow back to F.2.4.

XML10 contains a retry-limit inconsistency: STH.1.1.14 describes up to ten retry attempts, while Sys.2.4.2 limits the operation to ten total attempts. This implementation follows the stricter ten-total-attempt limit approved for Phase 6. The model should be reconciled to show the retry flow and agreed limit.

## Existing deterministic stub limitations

- In the default `stub` mode, `llm_api_interface.send_recipe_requirements(...)` returns the same two hard-coded recipes: Pasta Carbonara and Vegetable Stir-Fry. Optional OpenAI mode generates recipes, but recommendations are not guaranteed to obey dietary restrictions or budget.
- `llm_api_interface.request_pricing(...)` attaches ingredient prices and calculates a total for each recipe using the grocery-store interface.
- In explicit `GROCERY_PRICING_MODE=stub`, `grocery_store_interface.get_ingredient_pricing(...)` uses a fixed local price dictionary and returns `$1.00` for an ingredient without a listed price. It does not query a store or reflect location, package quantities, taxes, or current prices.
- The recipe data contains no preparation instructions, serving counts, or image metadata. The current pricing data is limited to ingredient names, estimated prices, and a recipe total.
- Fixed recipes/prices support an end-to-end demonstration, not production recommendations. In OpenAI mode, ingredients, budget, and dietary restrictions are sent to the external provider. Grocery pricing is configured independently; user-owned matches only adjust the backend additional-purchase estimate, while budget does not filter recipes and dietary restrictions are not guaranteed.

## Modeling items requiring confirmation

- F.2.5 receives Error Response and emits “Retry (Up to 10 Times),” but the diagram shows no flow that resubmits the request to F.2.4. Phase 6 implements transient retries as up to ten total attempts, following Sys.2.4.2; update the diagram and reconcile it with STH.1.1.14.
- F.2.8 classifies Shopping List Modifications as a control. If this represents a user’s requested edits, it may be better modeled as an input; if it represents rules governing edits, a control is reasonable. Confirm the intended meaning before implementation.
- Apart from the verified C.2.4 subsystem-level links to requirements 2.7.1, 2.8.1, and 2.9.1, direct requirement relationships for individual F.2 functions and subfunctions remain Pending Verification.

## Chapter 10.4 pricing benchmark traceability

The latest `Recipe Roulette Export.xml` contains simulation-bearing scenario
roots **S.1 Webscraping** (`I_293FF5YECAK8A_BDX2FTR813SDP`) and **S.2 Database**
(`I_F1H8BF80Z8GJC_8FGHTP2SG9K2S`). Their participant assets are User
(`I_3RKA1K727YKNZ_95TTAV7FWXJPM`) and App
(`I_B0312FGXERG7B_BWY173TC0M5DY`); S.1 additionally has Grocery Store Website
(`I_9TDEK0SCJ8J4T_90DD1GZVR5P1F`), while S.2 has Database
(`I_24D51EK49RKVC_BJHJFM0C6EY5P`). The table distinguishes a verified model
action from an experimental implementation mapping.

| Measurement stage | Python boundary | Innoslate action / participant boundary | Mapping status |
|---|---|---|---|
| `pricing_request_preparation` | `llm_api_interface.get_pricing` collects unique ingredient requirements before calling the pricing interface | S.1.1 Request prices for Unbought Ingredients (`I_B6CN15D638J7B_9DJTNN4BBD40S`); S.2.1 Request Pricing For Prospective Ingredients (`I_BCW3NPAY06H7R_94DNF2DG7EGFV`); App boundary | Function boundary verified; includes owned ingredients to preserve full-cost calculation |
| `in_memory_lookup` | `grocery_store_interface.get_ingredient_pricing` dictionary loop | S.2.2 Lookup Unbought Ingredients (`I_D1TWDBN3V4KDD_8STG5Q336F9B4`); Database participant boundary | **Analog only.** The function reads an in-memory Python dictionary, not the modeled Database participant or a database |
| `fixture_page_retrieval` | `FixturePageRetriever.retrieve_page` reads a saved local page | S.1.2 request webpage (`I_E0YKN30Z5EJTY_97843X9ZFQS26`) and S.1.4 receive webpage (`I_BNC16EWQB6KKP_AADC99C1P2WMX`) | Fixture analogue only; no HTTP round trip or Website participant |
| `html_parsing` | `parse_product_listing_html` parses saved product cards | S.1.5 Parse Webpage (`I_FWXSPC1D7JH0Y_AYHAHN893XGJ8`) | Implemented for project-owned fixture markup; retailer markup unverified |
| `kroger_request_pacing` / `kroger_http_request` | Kroger OAuth token or location-filtered product request | S.1.2 request webpage (`I_E0YKN30Z5EJTY_97843X9ZFQS26`) / S.1.4 receive webpage (`I_BNC16EWQB6KKP_AADC99C1P2WMX`) | API source substitution; measure API request/JSON latency, not webpage latency |
| `kroger_response_parsing` | Decode and validate the Kroger JSON response | S.1.5 Parse Webpage (`I_FWXSPC1D7JH0Y_AYHAHN893XGJ8`) | JSON parsing substitutes for webpage parsing; Kroger API participant not yet in model |
| `kroger_product_extraction` | Convert Kroger product/item fields to shared product candidates | S.1.6 Extract Pricing Data (`I_5Q3W7HG65EG35_89219FPNCCBNE`) | Extract product IDs/categories, package size, sold-by unit, and regular/promo price |
| `product_extraction` / `price_extraction` | Fixture candidate fields or validated Kroger price fields | S.1.6 Extract Pricing Data (`I_5Q3W7HG65EG35_89219FPNCCBNE`) | Source-specific extraction; missing/malformed prices fail |
| `product_matching` | `select_product_offer` filters identity, category/type, package and price eligibility, and ambiguity | S.1.6 Extract Pricing Data (`I_5Q3W7HG65EG35_89219FPNCCBNE`) | Shared fixture/Kroger logic; internal failure logs count missing/non-unit sold-by values, missing/unsupported package sizes, incompatible units, and invalid prices |
| `unit_package_normalization` | Package parsing, unit compatibility, and recipe-use price normalization | S.1.6 Extract Pricing Data (`I_5Q3W7HG65EG35_89219FPNCCBNE`) | Implemented; package and recipe units must be compatible |
| `pricing_response_processing` | `llm_api_interface.get_pricing` attaches quotes and computes recipe subtotals | S.1.6 Extract Pricing Data (`I_5Q3W7HG65EG35_89219FPNCCBNE`), S.1.7 Display Recipe and Pricing (`I_B574M42QW4KK2_ABDCRP983PS6W`); S.2.3 Display Recipe and Pricing Results (`I_6BBS9AH3X8HN6_BGQ9K1HZA5Y14`) | Shared fixture/Kroger response assembly; API source substitution remains architecturally distinct from literal S.1 |
| `ingredient_ownership_matching` | `recipe_service.identify_owned_recipe_ingredients` | No separate S.1/S.2 action identified | Measured implementation detail; no model action assigned |
| `recipe_cost_calculation` | `recipe_service.calculate_recipe_costs` | Pricing/result display actions S.1.7 and S.2.3 | Proposed correspondence only; no separate cost-calculation action is allocated |
| `pricing_workflow_total` | Benchmark wraps request pricing plus ownership and recipe-cost processing | S.1.1–S.1.8 and S.2.1–S.2.4, including S.1.8 (`I_2920TW22R4K1B_AB0GBRC5KKK1D`) and S.2.4 (`I_AB8ZE7DJPWJQ9_9Y2J87WH0VDCM`) | Fixture runs exclude external HTTP; Kroger runs include API HTTP but are not literal webpage timings |
| `llm_pricing_attempt` and `pricing_response_validation` | Isolated `llm_api_interface.pricing_estimator` request and local schema validation | **No S.3 pricing sequence/action or S.3 participant boundary is present in the inspected export** | Proposed experiment only; not traceable to an existing S.3 ID |

S.1 additionally models webpage request/receipt, parsing, and price extraction:
S.1.2 (`I_E0YKN30Z5EJTY_97843X9ZFQS26`), S.1.3
(`I_5KFGA727G0KB2_9F0RZHFEXBYS1`), S.1.4
(`I_BNC16EWQB6KKP_AADC99C1P2WMX`), and S.1.5
(`I_FWXSPC1D7JH0Y_AYHAHN893XGJ8`). Fixture execution covers local page reading
and parsing but not remote request/receipt or Grocery Store Website
participant timing. Kroger API mode adds actual OAuth/product HTTP round trips,
but substitutes JSON API actions for webpage interactions. S.2's database
lookup is likewise unimplemented. The current
`$1.00` fallback for unknown ingredient names is part of the in-memory
implementation, not a modeled database response.

The experimental LLM pricing module does not replace production pricing or
recipe generation. Its request/validation timings are proposed measurements
against the LLM API boundary; they do not establish an S.3 model mapping. The
current export has a separate non-simulation `Database scenario` entity also
numbered S.2 (`I_C2XSPABGH6GRC_A22Z9Z9V1VQGG`); the traceability above uses the
S.2 `Database` root with the action sequence and participant assets.

## Chapter 11 — Kroger Products API traceability

The team selected Kroger's documented Products API as the final live grocery
pricing source. This is a source-interface substitution for S.1 Webscraping:
the application sends an OAuth-authenticated product-search request and
receives location-filtered JSON, not a webpage. `GROCERY_PRICING_MODE` still
defaults to local HTML fixtures; `kroger` is opt-in. The explicit dictionary
stub is retained and no mode silently falls back to another source.

| S.1 model action | Verified model identifier | Kroger API correspondence | Mapping status |
|---|---|---|---|
| S.1 Webscraping scenario root | `I_293FF5YECAK8A_BDX2FTR813SDP` | `grocery_store_interface/kroger_api.py` | Team-selected API source substitution; not literal webpage scraping |
| S.1.1 Request prices for Unbought Ingredients | `I_B6CN15D638J7B_9DJTNN4BBD40S` | `get_ingredient_pricing` prepares searches for recipe ingredient requirements | Partial: all recipe ingredients, including owned ones, are priced to preserve full-cost fields |
| S.1.2 Request webpage for Ingredient X | `I_E0YKN30Z5EJTY_97843X9ZFQS26` | `GET /v1/products?filter.term=...&filter.locationId=...` | Replaced by a documented API request; no webpage request |
| S.1.3 Receive Request for Webpage (Ingredient X) | `I_5KFGA727G0KB2_9F0RZHFEXBYS1` | No direct webpage participant; Kroger receives the API request | No literal counterpart |
| S.1.4 Receive Webpage for Ingredient X | `I_BNC16EWQB6KKP_AADC99C1P2WMX` | Kroger returns product-search JSON | API response substitutes for webpage receipt |
| S.1.5 Parse Webpage | `I_FWXSPC1D7JH0Y_AYHAHN893XGJ8` | Parse and shape-check the JSON response | JSON parsing substitutes for webpage parsing |
| S.1.6 Extract Pricing Data | `I_5Q3W7HG65EG35_89219FPNCCBNE` | Extract product identity/categories, price, package size and sold-by unit; match and normalize | Implemented conservatively; ambiguous, missing, malformed, or incompatible data fails |
| S.1.7 Display Recipe and Pricing | `I_B574M42QW4KK2_ABDCRP983PS6W` | Existing v1/v2 response and browser display | Implemented; v1 and v2 response shapes preserved |
| S.1.8 Receive Recipe and Pricing Information | `I_2920TW22R4K1B_AB0GBRC5KKK1D` | Browser receives existing API response | Implemented at the existing interface |

The S.1 participant assets remain User
(`I_3RKA1K727YKNZ_95TTAV7FWXJPM`), App
(`I_B0312FGXERG7B_BWY173TC0M5DY`), and Grocery Store Website
(`I_9TDEK0SCJ8J4T_90DD1GZVR5P1F`). The current API adds an external Kroger
Products API participant that is not represented in the existing export.
The model should replace or revise the Website participant and its page
request/receipt actions to show client-credentials authentication, a
location-filtered product query, and a JSON response. Any new OAuth action,
location input, rate-limit/error flow, and API participant IDs must be added
and allocated in Innoslate; this document does not invent model IDs.

The trade-study/swing-weight results are not changed by this implementation.
Record the team's API selection as an architecture decision and document the
evidence and source substitution. Revise any architecture names, criteria, or
scores only through the team's explicit trade-study revision process; do not
retroactively replace original HTML-scraping scores.

The OpenAI recipe-generation response includes internal quantity and unit
fields; the public request and successful v1/v2 response shapes remain
unchanged. V1 retains ingredient-use cost semantics. V2 additionally reports
whole-package purchase cost and selected product/package provenance for
unowned ingredients, independently per alternative recipe. Kroger API
failures, ambiguous matches, unsupported units, and incomplete package data
never produce fabricated prices or fixture/stub fallbacks.

Historical Chapter 10 measurements and prior Chapter 11 fixture result files
are preserved. New benchmark runs distinguish `html_fixture` local parsing
from `actual_kroger_api_pricing`; Kroger timings measure API requests and must
not be reported as literal webpage-scraping latency. The analyzer's S.1
comparison note must retain this architecture mismatch.
