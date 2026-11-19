# Recipe Roulette — Chapter 9 Component Deviation Log

**Component:** C.2.4.2 — API Request Validation Component  
**Allocated function:** F.2.4.2 — Format and Validate API Request  
**Review basis:** `Recipe Roulette(1).xml` (latest uploaded Innoslate export), `Purple-Penguins-Phase_5_M2.zip` (repository snapshot), generated `SPEC.md`, and Chapter 9 §9.4 of the SYSEN 5151 lab manual.  
**Status:** **Preliminary baseline-to-model audit; NOT a completed Chapter 9 one-pass generation/deviation exercise.**  
**Date of review:** 2026-11-03  
**Reviewer:** Draft prepared for team review; classifications and resolutions require team signoff.

## 1. Purpose and evidence limitations

Chapter 9 requires one selected component to be generated *once* from a complete, verbatim component specification, then compared with that specification **before** editing the generated code. Each deviation must be classified as a **specification defect**, **assistant error**, or **unrequested addition**, and reconciled with the model and tests.

This document instead audits the **existing repository implementation** against the available model and contract, because the original Chapter 9 one-pass prompt, pristine generated output, generation timestamp/commit, and independent review have **not been supplied or established**. Consequently, the items below are **observed discrepancies or verification gaps**, not verified errors made by a particular coding assistant. Do not portray this audit as evidence that the required one-pass exercise was performed.

### Reviewed artifacts

- Innoslate: `Recipe Roulette(1).xml`, function `F.2.4.2`, component `C.2.4.2`, component requirement `1.4.2`.
- Code: `recipe_service.py`, lines 144–219, function `format_and_validate_api_request`.
- Endpoint: `user_interface/routes.py`, lines 26–44, where the validator is called before other C.2.4 functions.
- API contract: `contracts/api-v1.yaml`, `RecipeGenerationRequest` schema (lines 61–91).
- Tests: `tests/test_functional_requirements.py` (missing-field, invalid-budget, invalid-ingredient, malformed-JSON, and normalization tests).
- Traceability: `docs/traceability.md` (F.2.4.2 and its requirement linkage marked **Pending Verification**).
- New project-level `SPEC.md` is a working consolidation, not a substitute for verbatim, approved Innoslate component requirements.

## 2. Model baseline and expected interface

The Innoslate function is **F.2.4.2 — Format and Validate API Request**. The corresponding requirement **1.4.2** is currently written:

> The Submit Recipe and Pricing Requests Subsystem shall Format and Validate API Request.

The model's documented flow is **Prepared Recipe Request → F.2.4.2 → Validated API Request → F.2.4.3**, followed by **Recipe Request with Ingredient Ownership Information → F.2.4.4**. The model alone does not define the exact JSON schema, data types, rejection messages, failure output, or validation thresholds for F.2.4.2. These details exist in the code/OpenAPI contract, but need formal authorization and traceability in the component specification.

The existing Python function accepts a Python object; requires `ingredients`, `budget`, and `dietary_restrictions`; rejects unknown keys; enforces nonempty ingredient names and positive finite numeric budget; permits an empty restrictions list; strips whitespace; and returns a normalized Python dictionary. Invalid values raise `RecipeRequestValidationError` containing field-level messages. The Flask route parses JSON and converts validation exceptions to HTTP 400 errors.

## 3. Deviation and gap register

| ID | Type / confidence | Requirement or interface | Model / expected behavior | Observed repository behavior | Assessment and proposed reconciliation | Status |
|---|---|---|---|---|---|---|
| **DEV-C242-001** | **Specification defect — supported** | `1.4.2` | A component specification sufficient to implement and verify formatting/validation without assumptions. | Innoslate requirement repeats the function title without defining required fields, types, constraints, rejection rules, or measurable acceptance criteria. The API contract and Python code define these details separately. | Rewrite or derive a testable component requirement and cite an approved contract for exact validation rules. Record rationale, MOP, and verification method; trace it to its higher-level requirement and C.2.4.2. | **Open — model/specification update** |
| **DEV-C242-002** | **Architecture/code sequencing discrepancy — supported; classification pending** | `F.2.4.1` → `F.2.4.2` | The modeled F.2.4.2 input is a **Prepared Recipe Request** produced by F.2.4.1. | `user_interface/routes.py` calls `format_and_validate_api_request(payload)` immediately on the incoming request; that validator calls `prepare_recipe_request(...)` internally at `recipe_service.py:215–219`. Thus the code performs validation **before** calling the modeled preparation helper. | Decide whether the modeled sequence or the code is authoritative. Preferred reconciliation: preserve validation of untrusted inputs at the boundary while redefining the functional split/ICOM sequence, **or** refactor into separately callable stages that honor the model. Do not change either silently. | **Open — architecture decision** |
| **DEV-C242-003** | **Responsibility allocation gap — supported; classification pending** | `F.2.4.2` / JSON formatting and `2.4.1.1` if applicable | The component's function name includes formatting; a flowed-down requirement requires recipe requests sent externally to be valid JSON. | C.2.4.2 returns a **Python dictionary**. Incoming JSON parsing occurs in Flask (`request.get_json`); outgoing HTTP JSON serialization occurs in other layers/providers. The validator checks a Python-object schema, but does not itself serialize an outgoing LLM request. | Clarify whether “formatting” means producing a normalized structured request or serializing JSON for the external provider. Assign JSON encoding to its actual responsible component and verify the outgoing provider payload. | **Open — allocation/verification** |
| **DEV-C242-004** | **Traceability gap — supported** | `1.4.2`, F.2.4.2, C.2.4.2 | Chapter 9 asks for requirement, function, physical asset, and test traceability. | `docs/traceability.md` explicitly marks the requirement relationship for F.2.4.2 as **Pending Verification**, despite identifying code and several tests. | Verify the exact Innoslate requirement relationship and parent system-level requirement; update the traceability matrix with actual IDs and requirement-derived test names. | **Open — traceability check** |
| **DEV-C242-005** | **Potential unrequested addition — needs baseline confirmation** | API contract validation rules | A one-pass component must implement only the constraints authorized by its frozen specification. | Code rejects additional top-level fields, requires a nonempty ingredient list, rejects non-finite budgets and booleans, trims strings, and returns per-field error descriptions. These rules are stated in `contracts/api-v1.yaml`, but not in the quoted Innoslate `1.4.2` sentence itself. | **Do not label these features unrequested merely because Innoslate is terse.** Determine whether `api-v1.yaml` was explicitly included in the frozen component prompt. If it was, these are contract-conformant features; if not, classify each truly unsupported behavior as an **unrequested addition** and decide whether to formalize or remove it. | **Pending original prompt/approved contract** |
| **DEV-C242-006** | **Verification/evidence gap — supported** | Acceptance / CI evidence | Requirement-derived validation tests should execute and pass in the approved environment. | Existing tests cover missing fields, invalid budgets, ingredients, malformed JSON and normalized values. A local attempt to collect `tests/test_functional_requirements.py` failed with `ModuleNotFoundError: No module named 'flask'` before tests ran. | Install project dependencies in the prescribed environment; run the complete suite and CI; record exact command, Python version, results, and commit SHA. **Not evidence of a code defect.** | **Blocked — environment setup** |

### Classification note

`DEV-C242-002`, `-003`, and `-004` identify actual differences or missing evidence, but the three Chapter 9 **generation-deviation** categories cannot be assigned faithfully without a frozen initial specification and unedited generated output. Upon that comparison, classify each observed generated-code difference as **specification defect**, **assistant error**, or **unrequested addition**. Do not retroactively call undocumented pre-existing decisions assistant errors.

## 4. Verification matrix for C.2.4.2

| Verification ID | Intended criterion / observation | Current evidence | Result |
|---|---|---|---|
| `V-C242-01` | Complete valid request accepted and normalized to the approved schema. | `test_recipe_endpoint_normalizes_preferences_and_passes_restrictions` | Test present; execution not confirmed |
| `V-C242-02` | Missing required fields rejected with field-specific error feedback. | `test_recipe_endpoint_reports_missing_required_inputs` | Test present; execution not confirmed |
| `V-C242-03` | Invalid budgets (≤0, boolean, string, NaN/Inf) rejected. | `test_recipe_endpoint_rejects_invalid_budget_values` | Test present; execution not confirmed |
| `V-C242-04` | Invalid ingredient arrays and entries rejected. | `test_recipe_endpoint_rejects_invalid_ingredients` | Test present; execution not confirmed |
| `V-C242-05` | Malformed incoming JSON returns an appropriate HTTP 400. | `test_recipe_endpoint_rejects_malformed_json`; Flask boundary rather than validator function alone | Test present; execution not confirmed |
| `V-C242-06` | Outgoing structured LLM requests are valid JSON according to the selected external API schema. | Not demonstrated by C.2.4.2 alone; inspect provider-adapter tests/transport separately | Component responsibility unresolved |
| `V-C242-07` | Valid request is processed through the specified modeled F.2.4.1 → F.2.4.2 sequence. | Current route calls validation first | Mismatch to resolve |

**Proposed deterministic MOP:** percentage of approved valid test cases accepted *and* approved invalid test cases rejected correctly, target **100% for the defined test suite**. This is a proposed acceptance threshold; it must be approved and traced to a testable requirement before being presented as achieved.

## 5. Chapter 9 one-pass exercise — still to be executed or evidenced

- [ ] Freeze the exact approved C.2.4.2 specification with Innoslate requirement IDs/text **verbatim**, ICOMs, API contract/version, programming constraints, file boundaries, error rules, and success criteria.
- [ ] Record Git baseline commit SHA and whether C.2.4.2 existing code is excluded/replaced or generated in a separate branch/file.
- [ ] Preserve the full Chapter 9 implementation prompt in `docs/prompts/` and reference it in `docs/prompt-log.md`.
- [ ] Generate **one component once**, without post-generation correction; preserve the original produced file and its commit/hash.
- [ ] Compare that original output to each frozen specification clause, including testable error behavior.
- [ ] Add all actual generation deviations to this log, with expected vs actual, classification, and evidence locations.
- [ ] Obtain independent team review and document selected fixes or justified new requirements.
- [ ] Reconcile the Innoslate requirements, ICOMs, implementation, and traceability mapping.
- [ ] Run tests and CI in a dependency-complete environment and record numerical results.
- [ ] Close each deviation with an implementation/model commit reference and reviewer approval.

## 6. Completion record (fill in from actual execution)

| Evidence item | Value |
|---|---|
| Approved Innoslate export/version | `Recipe Roulette(1).xml` — confirm final freeze |
| Approved component specification artifact | **Not yet provided** |
| One-pass prompt file / log entry | **Not yet identified** |
| Baseline Git commit SHA | **Not provided in reviewed ZIP** |
| Unedited one-pass output path / commit SHA | **Not provided** |
| Independent reviewer | **Not recorded** |
| Test environment and command | Attempted: `python -m pytest -q tests/test_functional_requirements.py` |
| Result of local attempt | **Collection error:** Flask dependency unavailable; no tests executed |
| CI run URL / passing tests | **Not provided** |
| Sign-off / closure date | **Open** |

## 7. Recommended next decision

Confirm whether C.2.4.2 is intended to **validate an incoming recipe request**, **produce the finalized provider request**, or **both**. This single decision will resolve the most important ambiguity between the F.2.4.1–F.2.4.2 sequence, the current Flask code, and the JSON-formatting requirement. Then freeze the component specification and run the Chapter 9 one-pass exercise so the final deviation log captures actual observed generation differences rather than speculative ones.
