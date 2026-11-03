# F.2 Function Traceability

**Status:** F.2.2, F.2.3, and F.2.7 have browser-interface implementations for the demonstration workflow; F.2.4 is implemented for the deterministic recipe-generation API workflow. F.2.1, F.2.5, F.2.6, and F.2.8 remain unimplemented. F.2.2's modeled Login Approved prerequisite is visibly simulated; no authentication is performed.

## Traceability matrix

Requirement IDs are marked **Pending Verification** because no direct requirement relationship was found for the F.2 functions or their corresponding C.2 subsystem assets in the reviewed Innoslate export. Do not replace these entries with inferred IDs.

| Innoslate function ID | Exact function name | Related requirement ID | Proposed Python module/function | Planned automated test | Implementation status |
|---|---|---|---|---|---|
| F.2.1 — `I_AW2W0HS6YEH5N_9C41E7112B61C` | Request and Validate User Login | Pending Verification | `user_interface/auth.py::request_and_validate_user_login` | `test_f21_demo_login_approval_is_explicit` | Not Implemented; later phase |
| F.2.2 — `I_7XRQR0GFSTJER_B0W15Z68VZJM2` | Collect User Ingredients | Pending Verification | `user_interface/templates/index.html`; `user_interface/static/js/recipe-roulette.js` form submission | `test_homepage_contains_recipe_preference_controls_and_demo_notices` | Implemented in browser demo; F.2.1 approval is simulated |
| F.2.3 — `I_CTXZXZ70BGHV4_AFHBBP2CRP43Y` | Collect budget and Dietary Restrictions | Pending Verification | `user_interface/templates/index.html`; `user_interface/static/js/recipe-roulette.js` form submission | `test_homepage_contains_recipe_preference_controls_and_demo_notices` | Implemented in browser demo |
| F.2.4 — `I_7Y3Y133TSAG54_98MDRGWJ519M3` | Submit Recipe and Pricing Requests | Pending Verification | `recipe_service.py::submit_recipe_and_pricing_requests` | `test_f24_submits_requirements_to_recipe_and_pricing_stubs` | Implemented for the deterministic API workflow |
| F.2.5 — `I_4RZHP3MTHRKRE_A896NKDQGJ2S4` | Resend LLM API Request | Pending Verification | `recipe_service.py::resend_llm_api_request` | `test_f25_resends_failed_request_within_model_limit` | Not Implemented; later phase |
| F.2.6 — `I_BW2QHYF5AMGMM_ATJZXVSX8MFCB` | Contact Customer Support | Pending Verification | `customer_service_interface/__init__.py::submit_support_request` | `test_f26_submits_question_and_feedback_to_customer_service` | Not Implemented; later phase |
| F.2.7 — `I_34QM2GKG6PKA5_AJ7AXJC1FBE5K` | Display Recipes and Pricing Results | Pending Verification | `user_interface/static/js/recipe-roulette.js::renderRecipes` | `test_homepage_loads_recipe_interface_assets` (asset delivery; rendering requires browser verification) | Implemented in browser; displays API results as returned |
| F.2.8 — `I_6QP83SB7YMK8Z_8G41HVK3PJYRS` | Modify Shopping List | Pending Verification | `shopping_list.py::apply_modifications` | `test_f28_applies_shopping_list_modifications` | Not Implemented; later phase |

### Phase 3 F.2.4 subfunctions

The Phase 3 function/component labels were supplied in the implementation request; their names and global IDs below are verified against the latest Innoslate export, `Recipe Roulette (8).xml`. Requirement IDs remain pending verification because no direct requirement links were found for these entities.

| Innoslate function and component IDs | Related requirement ID | Implemented Python function | Automated test | Implementation status |
|---|---|---|---|---|
| F.2.4.1 — Prepare Recipe Request (`I_4FQB4AXSNMJTB_BP518PV5V30BN`); C.2.4.1 — Recipe Request Preparation Component (`I_FRJYSFT6PYHG9_AJWNE3781P3TM`) | Pending Verification | `recipe_service.py::prepare_recipe_request` | `test_recipe_endpoint_normalizes_preferences_and_passes_restrictions` | Implemented |
| F.2.4.2 — Format and Validate API Request (`I_C5HVGPQMDEKPB_822HFWSBZWGEH`); C.2.4.2 — API Request Validation Component (`I_8FYMCCF9KYGYS_829BEWYMF1P63`) | Pending Verification | `recipe_service.py::format_and_validate_api_request`; invoked by `user_interface.routes.generate_recipes` | `test_recipe_endpoint_reports_missing_required_inputs`; `test_recipe_endpoint_rejects_invalid_budget_values`; `test_recipe_endpoint_rejects_invalid_ingredients`; `test_recipe_endpoint_rejects_malformed_json` | Implemented |
| F.2.4.3 — Submit Recipe and Pricing Requests (`I_C3XRN0P8R0JED_AS6RHTHBNZ0C6`); C.2.4.3 — Request Submission Component (`I_35QN82Z6Q6JT8_9S98VJAVR325X`) | Pending Verification | `recipe_service.py::submit_recipe_and_pricing_requests` | `test_f24_submits_requirements_to_recipe_and_pricing_stubs`; `test_recipe_endpoint_is_deterministic` | Implemented — deterministic local stubs only |

The API endpoint returns recipe pricing to satisfy the existing contract. This API implementation does not add recipe display UI or claim that stub results are personalized or production-ready.

Request preparation trims surrounding whitespace from ingredient and dietary-restriction strings and converts the positive numeric budget to a float. Values that become empty after trimming are rejected so a whitespace-only string is not treated as a meaningful ingredient or restriction.

The test names and Python paths for functions not yet implemented remain proposals. Phase 3 subfunction entries above identify the functions and tests implemented in that phase. Phase 4's Python tests verify the page controls and asset delivery; they do not execute the browser JavaScript, so form submission and DOM rendering still require browser verification.

## Verified ICOM and internal-flow notes

ICOM assignments below are taken from the F.2 decomposition diagram and its relationship records in the latest export, `Recipe Roulette (8).xml`. Names and global IDs are reproduced from that export.

| Function | Inputs | Controls | Outputs | Internal flow(s) |
|---|---|---|---|---|
| F.2.1 | Login Credentials — `I_9ZXZG9W4BEGYP_8ND7T3SV6CJMN` | Session Intitates — `I_F2MBDEQD6EJJ1_8MV4K41QX624H` | Request for User Login — `I_2JT79HMQ8YKD1_ASDM379JY737Q`; Approve Login — `I_17P62SC2DTJM3_A9QA5QK75YYSJ` | Login Approved — `I_CSSY5WGCB8KAK_8SFB4X6DXXQRF` → F.2.2 |
| F.2.2 | User Preferences / Ingredients — `I_ABYZTK7C68KDT_BNTJX2PYK8N1Q`; Login Approved — `I_CSSY5WGCB8KAK_8SFB4X6DXXQRF` | None shown | Ingredient Request — `I_D5DFGPJ8VAJJN_BM4J5XG2DYTZV` | User Ingredients — `I_CR10TPVM04GDG_96MANTHTT4BT5` → F.2.4 |
| F.2.3 | User Preferences / Ingredients — `I_ABYZTK7C68KDT_BNTJX2PYK8N1Q` | None shown | Request Monetary Budget — `I_2AJ58PD5A4GZB_9MQJZ47WPV7TA`; Request Dietary Restrictions — `I_180E5JZ4RJJRT_BTM39GRESR7CP` | Budget and Dietary Restrictions — `I_8RGEWPBTDAGNJ_9NETAHKBAKQY2` → F.2.4 |
| F.2.4 | User Ingredients — `I_CR10TPVM04GDG_96MANTHTT4BT5`; Budget and Dietary Restrictions — `I_8RGEWPBTDAGNJ_9NETAHKBAKQY2` | None shown | Ingredients/Budget/Dietary Restrictions — `I_1P1WPWQASTH3Q_8XCGY5SMFZFBN`; Pricing request — `I_B0DN39R3X6H81_8Z851DK8CF9D5` | Requests are sent to the existing recipe-generation and pricing interfaces |
| F.2.5 | Error Response — `I_B03ZP5ME6WKT3_AHE6D9SMEKV0B` | None shown | Retry (Up to 10 Times) — `I_5XRZYESY7AJ04_8Z0E305ZDGBMH` | No retry connection back to F.2.4 is shown |
| F.2.6 | Question/Concern — `I_BZ1QS58HT6JFB_8VW9E66M7ZXAQ`; Provides Feedback — `I_A8JHHDBJC4J1J_9T2XMH65HZB3W` | None shown | Customer Service Request — `I_C7BZA7A5C0GZA_8JQEEBH9NMCJG`; Support Response — `I_EF1JXBMVAYKB7_BP49GDVAMEECN` | Customer-service exchange is outside the F.2 internal sequence |
| F.2.7 | Recipe List — `I_EQTZM8DX3PJF1_AJY5R8W63XB38`; Recipe Pricing Data — `I_9HEE57NZFGJHX_BM6CG7SDTCHVQ` | None shown | Recipe & pricing results — `I_8594E5V832H36_B7P4W47Y6MSQZ` | Receives recipe and pricing data from outside the F.2 boundary |
| F.2.8 | Recipe List — `I_EQTZM8DX3PJF1_AJY5R8W63XB38`; Recipe Pricing Data — `I_9HEE57NZFGJHX_BM6CG7SDTCHVQ` | Shopping List Modifications — `I_FPJP7SJGVAJQK_AEY9M1QK1EQ7E` | Display Modifications — `I_AJ20ZNFZ9TGSC_8QXNXKZJYEVT1` | No connection to another F.2 function is shown |

## Phase 4 browser workflow mapping

| Function | Function global ID | Physical mechanism | Mechanism global ID | Browser implementation | Requirement ID |
|---|---|---|---|---|---|
| F.2.2 — Collect User Ingredients | `I_7XRQR0GFSTJER_B0W15Z68VZJM2` | C.2.2 — Collect User Ingredients Subsystem | `I_FCDN2YG3F6JZ2_AMZ9CZJHY2C5Y` | Ingredient entry in the preference form; values are split into the API's string array | Pending Verification |
| F.2.3 — Collect budget and Dietary Restrictions | `I_CTXZXZ70BGHV4_AFHBBP2CRP43Y` | C.2.3 — Collect Budget and Dietary Restrictions Subsystem | `I_CHM3F1BTT6G0Q_B5R9H37QCEE57` | Positive USD budget and optional restrictions are submitted through the same form | Pending Verification |
| F.2.4 — Submit Recipe and Pricing Requests | `I_7Y3Y133TSAG54_98MDRGWJ519M3` | C.2.4 — Submit Recipe and Pricing Requests Subsystem | `I_C6YMRGVVSEGHA_82M4PD6H48YHR` | Existing `POST /api/v1/recipes` API and deterministic recipe/pricing stubs | Pending Verification |
| F.2.7 — Display Recipes and Pricing Results | `I_34QM2GKG6PKA5_AJ7AXJC1FBE5K` | C.2.7 — Display Recipes and Pricing Results Subsystem | `I_96E93MMBC6H8V_A7890DCT74CN3` | JavaScript renders the returned recipe names, ingredients, estimated prices, and totals without filtering | Pending Verification |

## F.2.2 login dependency and demonstration mode

F.2.2 has a modeled **Login Approved** input from F.2.1 (`I_CSSY5WGCB8KAK_8SFB4X6DXXQRF`). Phase 4 displays that prerequisite as simulated demo mode so the browser workflow can run without implementing authentication.

**Demonstration limitation:** The page states that login approval is simulated. It collects no credentials, creates no authenticated session, and does not change the Innoslate dependency.

## Existing deterministic stub limitations

- `llm_api_interface.send_recipe_requirements(...)` currently logs the received ingredients, budget, and restrictions, then returns the same two hard-coded recipes: Pasta Carbonara and Vegetable Stir-Fry. It does not filter or personalize those recipes using the submitted preferences.
- `llm_api_interface.request_pricing(...)` attaches ingredient prices and calculates a total for each recipe using the grocery-store interface.
- `grocery_store_interface.get_ingredient_pricing(...)` uses a fixed local price dictionary and returns `$1.00` for an ingredient without a listed price. It does not query a store or reflect location, quantity, taxes, or current prices.
- The recipe data contains no preparation instructions, serving counts, or image metadata. The current pricing data is limited to ingredient names, estimated prices, and a recipe total.
- These deterministic stubs support an end-to-end demonstration, not production recommendations or live pricing. The browser identifies results as demonstration data and warns that they are not filtered by submitted preferences.

## Modeling items requiring confirmation

- F.2.5 receives Error Response and emits “Retry (Up to 10 Times),” but the diagram shows no flow that resubmits the request to F.2.4. Confirm the missing retry connection and whether “10” means retries or total attempts; do not implement a different limit.
- F.2.8 classifies Shopping List Modifications as a control. If this represents a user’s requested edits, it may be better modeled as an input; if it represents rules governing edits, a control is reasonable. Confirm the intended meaning before implementation.
- No direct requirement IDs for the F.2 functions or their C.2 subsystem assets were found in the relationships inspected in `Recipe Roulette (8).xml`. Keep those IDs pending until verified.
