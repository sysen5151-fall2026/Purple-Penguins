# Prompt summary — Phase 5 ingredient-aware pricing

Implement ingredient-aware purchase-cost estimates in Recipe Roulette. Treat the existing request `ingredients` array as ingredients already owned. Match recipe ingredient names using trimmed, case-insensitive exact equality. Do not infer substitutions or quantities; assume the user has enough of each listed ingredient.

Preserve full ingredient prices and the existing full-recipe `estimated_total_cost`. Calculate an additional purchase cost from unowned ingredients and compare that cost—not full recipe cost—to the submitted budget. Return ownership status per ingredient and budget status per recipe. Keep the matching and calculations in Python; do not modify prices to zero, remove over-budget recipes, or calculate deductions in JavaScript.

Use the existing separate recipe-generation and pricing stubs, request schema, and console walking skeleton. Propose the smallest additive API v1 response change and update the browser to label owned ingredients, distinguish owned versus purchase items, and show full cost, purchase cost, and budget status. Preserve deterministic demo-data and dietary-restriction disclaimers.

The initial Phase 5 implementation was reviewed against `Recipe Roulette (8).xml`. The user subsequently identified `Recipe Roulette (10).xml` as the latest export and approved reconciling the existing Phase 5 changes to it. XML10 verifies:

- F.2.4.1 — Prepare Recipe Request (`I_4FQB4AXSNMJTB_BP518PV5V30BN`)
- F.2.4.2 — Format and Validate API Request (`I_C5HVGPQMDEKPB_822HFWSBZWGEH`)
- F.2.4.3 — Specify Already-Owned Recipe Ingredients (`I_C3XRN0P8R0JED_AS6RHTHBNZ0C6`)
- F.2.4.4 — Submit Recipe and Pricing Requests (`I_CZFVR1YCP8J7C_87K5PYQC4ZNN0`)
- C.2.4.3 — Ingredients List Redundancy Removal Device (`I_35QN82Z6Q6JT8_9S98VJAVR325X`)
- C.2.4.4 — Request Submission Component (`I_6FJAPA7HG2GJC_9B0D0PAPPRQJS`)

XML10 does not contain F.2.4.5 or a separate additional-cost calculation function/flow. Keep `calculate_recipe_costs` as an unallocated service-level helper and document that model gap. Do not invent function, component, ICOM, or requirement IDs.

Test exact/case-insensitive/whitespace matching, empty/some/all ownership, duplicates, full and additional costs, budget comparison boundaries, legacy response fields, browser output, and console compatibility. Update the OpenAPI contract and relevant traceability, route, prompt-log, and test documentation. Do not commit or push.
