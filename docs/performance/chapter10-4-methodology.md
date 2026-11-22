# Chapter 10.4 — Pricing Performance Methodology

## Purpose and scope

This benchmark measures the current Python pricing work and a separate LLM
price-estimation request. The same estimator helper is used by the web
workflow in OpenAI mode when store and ZIP context are supplied. The benchmark
excludes recipe generation,
browser rendering, user input, and the simulated login prerequisite. The
benchmark remains a separate, explicitly authorized workflow; it does not
make normal web requests or use store/ZIP context.

The fixed shared input is the name-only list:

```text
chicken, rice, broccoli, olive oil, garlic
```

The production pricing interface accepts ingredient names only; it has no
quantity or package-size field. The shared estimator prompt asks for an estimate per named prospective item,
with no quantity or unit supplied. Price accuracy is not evaluated. LLM
results are unverified estimates, not actual grocery-store prices.

Both modes then run the same ownership and recipe-cost functions with all
benchmark ingredients treated as unowned. The benchmark-only budget is
`$1,000,000` to exercise the existing budget comparison without adding budget
to either pricing request; it is not interpreted as a pricing constraint.

## Implemented measurement boundaries

Server timings use `time.perf_counter_ns()` only while a benchmark measurement
context is active. Normal application calls retain their behavior and do not
emit timing records.

| CSV stage | Instrumented function boundary | Meaning |
|---|---|---|
| `pricing_request_processing` | Unique ingredient collection in `llm_api_interface.get_pricing` | Request-side preparation before price lookup |
| `in_memory_lookup` | Dictionary loop in `grocery_store_interface.get_ingredient_pricing` | In-memory lookup, including existing `$1.00` fallback; **not a database query** |
| `pricing_response_processing` | Attaching looked-up prices and computing each returned subtotal in `llm_api_interface.get_pricing` | Local response processing |
| `ingredient_ownership_matching` | `recipe_service.identify_owned_recipe_ingredients` | Exact normalized ownership match; benchmark inputs are all prospective/unowned |
| `recipe_cost_calculation` | `recipe_service.calculate_recipe_costs` | Existing whole-cent recipe-cost and budget calculation |
| `pricing_workflow_total` | Local benchmark around `request_pricing` and ownership/cost processing; LLM benchmark around setup, request, validation, and the same ownership/cost processing | Pricing-only end-to-end Python interval; excludes recipe generation and browser/network-to-browser time |
| `llm_request_total` | LLM client setup through one Responses API call | Complete client-observed request operation, excluding output validation |
| `llm_pricing_attempt` | One `client.responses.create` invocation | Individual attempt duration; SDK retries are disabled |
| `pricing_response_validation` | Local JSON/schema/domain validation of the LLM response | Response processing after the external call |

`llm_pricing_attempt` is measured by the application around the SDK call. It
includes elapsed time experienced by the client (network transfer, provider
waiting, and SDK overhead); it does **not** expose or claim access to
provider-internal execution time. The price-estimation client has
`max_retries=0`, so `retry_attempts` is zero and each run sends no more than
one API request. Failed attempts are recorded; validation is absent if no
response arrived.

## Innoslate traceability and limitations

The action names and global IDs below are from the current `Recipe Roulette
Export.xml`; full measurement mapping is also in
[docs/traceability.md](../traceability.md).

| Scenario/action | Verified model boundary | Measurement relation |
|---|---|---|
| S.1 Webscraping — `I_293FF5YECAK8A_BDX2FTR813SDP` | Participants: User `I_3RKA1K727YKNZ_95TTAV7FWXJPM`, App `I_B0312FGXERG7B_BWY173TC0M5DY`, Grocery Store Website `I_9TDEK0SCJ8J4T_90DD1GZVR5P1F`. Actions: S.1.1 request prices `I_B6CN15D638J7B_9DJTNN4BBD40S`; S.1.2 request webpage `I_E0YKN30Z5EJTY_97843X9ZFQS26`; S.1.3 receive webpage request `I_5KFGA727G0KB2_9F0RZHFEXBYS1`; S.1.4 receive webpage `I_BNC16EWQB6KKP_AADC99C1P2WMX`; S.1.5 parse webpage `I_FWXSPC1D7JH0Y_AYHAHN893XGJ8`; S.1.6 extract pricing `I_5Q3W7HG65EG35_89219FPNCCBNE`; S.1.7 display recipe/pricing `I_B574M42QW4KK2_ABDCRP983PS6W`; S.1.8 receive recipe/pricing `I_2920TW22R4K1B_AB0GBRC5KKK1D`. | No scraping, webpage requests, parsing, or extraction is implemented. These actions are unmeasured, not assigned fabricated timings. |
| S.2 Database — `I_F1H8BF80Z8GJC_8FGHTP2SG9K2S` | Participants: User `I_3RKA1K727YKNZ_95TTAV7FWXJPM`, App `I_B0312FGXERG7B_BWY173TC0M5DY`, Database `I_24D51EK49RKVC_BJHJFM0C6EY5P`. Actions: S.2.1 request pricing `I_BCW3NPAY06H7R_94DNF2DG7EGFV`; S.2.2 lookup unbought ingredients `I_D1TWDBN3V4KDD_8STG5Q336F9B4`; S.2.3 display results `I_6BBS9AH3X8HN6_BGQ9K1HZA5Y14`; S.2.4 receive pricing `I_AB8ZE7DJPWJQ9_9Y2J87WH0VDCM`. | `in_memory_lookup` is a local dictionary analog of the lookup *operation*, not a database implementation or database-latency measurement. |
| S.3 LLM Pricing | No S.3 action sequence, action identifier, or S.3 participant allocation is present in the inspected export. | The OpenAI estimate path is implemented at the LLM API boundary, but no S.3 model mapping is verified. The benchmark measures the estimator separately; it does not supply simulation values. |

The local Python workflow runs within one process. It cannot represent the
external boundaries, transfer time, website parsing, database/network
latency, or modeled participant waiting in S.1/S.2. The scenarios are
therefore not architecturally equivalent. The benchmark reports actual
Python intervals beside—not as replacements for—the simulation summaries.
No actual Scenario 3 simulation values are supplied.

The local `pricing_workflow_total` includes the existing diagnostic `print`
calls made by the pricing interfaces, under the output buffering active for
the benchmark process. The isolated stage timers exclude those messages.
Very small in-memory durations are host- and scheduler-sensitive; report the
observed values with the run environment, not as universal latency guarantees.

## Simulation reference data

`results/chapter10-4/innoslate_reference.csv` contains the team-provided
10-run summaries: S.1 minimum 4.05 s, maximum 30.96 s, average 17.185 s; S.2
minimum 2.67 s, maximum 17.94 s, average 6.86 s. Median and standard
deviation were not provided and remain blank. S.3 is marked pending with no
numeric values.

The comparison treats the actual in-memory measurement as a limited local
proxy against S.2 and labels the architectural mismatch. Experimental LLM
timings have no S.3 simulation reference. Mean deltas are descriptive only,
not evidence of equivalent implementations.

## CSV format and analysis

`scripts/benchmark_pricing.py` writes one row per completed stage:

| Column | Description |
|---|---|
| `run_id` | Unique UUID for the benchmark run |
| `timestamp_utc` | Run start timestamp |
| `scenario`, `mode` | `actual_in_memory_dictionary` / `local` or `experimental_llm_pricing` / `llm` |
| `model` | Configured `OPENAI_MODEL` for LLM runs; blank for local runs |
| `input_dataset_id` | Fixed benchmark input-set identifier; ingredient contents are not logged |
| `stage`, `duration_ns` | Stage label and monotonic elapsed nanoseconds |
| `status`, `run_status` | Stage and overall run status (`success` or `failure`) |
| `attempt_number`, `attempt_count`, `retry_attempts` | Per-attempt index and request/retry totals |
| `error_type`, `provider_status_code` | Sanitized failure category / HTTP status; no raw exception or request text |

Analyze one or both timing files with:

```powershell
$localCsv = Get-ChildItem results\chapter10-4\local-*.csv |
  Sort-Object LastWriteTime |
  Select-Object -Last 1 -ExpandProperty FullName
python -m scripts.analyze_pricing_benchmark --input $localCsv
```

The script writes `stage-summary.csv` and `scenario-comparison.csv` under
`results/chapter10-4/analysis/`. Stage summaries group by scenario, stage, and
status and calculate count, minimum, maximum, arithmetic mean, median, and
sample standard deviation. Standard deviation is blank for fewer than two
observations. Raw durations are nanoseconds; report tables convert to seconds.
Only successful `pricing_workflow_total` rows populate measured scenario
summary rows; failures remain visible in raw CSV and stage summaries.

## Collection procedure

### Local in-memory pricing (30 runs)

From the repository root, run:

```powershell
python -m scripts.benchmark_pricing --mode local --runs 30 --max-requests 30
```

This makes 30 sequential calls to the current in-process pricing functions
with the fixed five-name list. It does not invoke recipe generation, Flask,
OpenAI, a browser, a database, or a scraper. Each row is flushed to a new,
non-overwriting CSV as each run completes.

### Experimental live LLM pricing (up to 30 requests)

Configure the server-side `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in
the shell environment. Review the selected model/account's current pricing.
Then run:

```powershell
python -m scripts.benchmark_pricing --mode llm --live --runs 30 --max-requests 30 --output results/chapter10-4/llm-pricing-30.csv
```

The script requires the explicit `--live` flag, a cap from 1 to 30 that is
at least the requested run count, and an interactive confirmation phrase
for every invocation. It refuses to overwrite an existing output file,
disables SDK retries, stops after the first failed live run by default, and
records the partial CSV before stopping. Use `--continue-on-error` only when
additional requests after a failure are separately approved. Each invocation
can send at most `--runs` requests; no live request is made by imports, tests,
or the local command. Live calls may incur charges.

## Verification expectations

Automated tests use fake OpenAI clients/responses only. They validate timing
capture, CSV columns, summary statistics, strict output validation,
failure sanitization, zero SDK retries, explicit live opt-in, cancellation,
and preservation of the existing deterministic pricing/API behavior.
