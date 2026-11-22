# Chapter 10.4 — Pricing Performance Methodology

## Purpose and scope

The benchmark measures the in-memory dictionary, local HTML fixture pricing,
the opt-in Kroger Products API workflow, and a separate experimental LLM
price-estimation request. Fixture prices are illustrative coursework data,
not live grocery prices. Fixture runs contact no websites and do not measure
webpage HTTP latency. Kroger timings measure OAuth/product API round trips,
not literal webpage scraping. The LLM module is not used by normal Recipe
Roulette requests and never replaces production grocery pricing.

The Chapter 10.4 experimental LLM benchmark retains its historical name-only
input list:

```text
chicken, rice, broccoli, olive oil, garlic
```

Those LLM outputs are unverified estimates, not grocery prices. The
quantity-bearing fixture basket uses the same ingredient names:

| Ingredient | Quantity | Unit |
|---|---:|---|
| chicken | 16 | oz |
| rice | 16 | oz |
| broccoli | 1 | head |
| olive oil | 1 | fl_oz |
| garlic | 1 | bulb |

These are repeatable harness inputs, not Innoslate simulation values or an
accuracy claim. The dictionary is name-based and ignores quantity. The HTML
fixture workflow parses saved local pages; Kroger mode searches the configured
location. Both normalize package prices only when package and recipe units
are dimension-compatible. The historical `local-in-memory-30.csv` result
remains unchanged.

Local, fixture, and Kroger benchmarks run ownership and recipe-cost functions
with all benchmark ingredients treated as unowned. The benchmark-only budget is
`$1,000,000`; it exercises the existing budget comparison and is not a pricing
constraint.

## Measurement boundaries

Server timings use `time.perf_counter_ns()` only while a benchmark measurement
context is active. Normal application calls do not emit timing records.

| CSV stage | Instrumented boundary | Meaning |
|---|---|---|
| `pricing_request_preparation` | Unique ingredient requirement collection in `llm_api_interface.get_pricing` | Request-side preparation |
| `in_memory_lookup` | Dictionary loop in `grocery_store_interface.get_ingredient_pricing` | In-memory lookup, including the historical `$1.00` fallback; **not a database query** |
| `fixture_page_retrieval` | `FixturePageRetriever.retrieve_page` | Local file read only; not an HTTP round trip |
| `html_parsing` | `parse_product_listing_html` | Parse the project-owned fixture-card markup |
| `product_extraction` | `extract_product_candidates` | Extract product identity, category, price text, package-size text, and units |
| `kroger_request_pacing` | Wait before a Kroger HTTP request | Process-local minimum interval between token/product requests |
| `kroger_http_request` | One Kroger token or product HTTP request/response | Client-observed duration; external request count is recorded |
| `kroger_response_parsing` | Decode and validate one Kroger JSON response | Local response parsing; no provider-internal timing |
| `kroger_product_extraction` | Convert Kroger product/item fields to shared product candidates | Extract product IDs/categories, package size, unit, and regular/promo price |
| `product_matching` | `select_product_offer` identity/type filtering | Reject unrelated and ambiguous fixture/API candidates |
| `price_extraction` | `extract_price` | Parse and validate an explicit USD price from fixture or Kroger candidate data |
| `unit_package_normalization` | Package parsing, unit compatibility, and recipe-use cost conversion | Requires supported, dimension-compatible units |
| `pricing_response_processing` | Attaching quotes and computing recipe subtotal in `llm_api_interface.get_pricing` | Local response processing |
| `ingredient_ownership_matching` | `recipe_service.identify_owned_recipe_ingredients` | Exact normalized ownership match; benchmark inputs are prospective/unowned |
| `recipe_cost_calculation` | `recipe_service.calculate_recipe_costs` | Whole-cent recipe cost and budget calculation |
| `pricing_workflow_total` | Benchmark wraps pricing, ownership, and cost processing | Pricing-only Python interval; excludes generation, browser rendering, and user input |
| `llm_request_total` | LLM client setup through one Responses API call | Client-observed request duration, excluding validation |
| `llm_pricing_attempt` | One `client.responses.create` invocation | Attempt duration; SDK retries are disabled |
| `pricing_response_validation` | Local LLM JSON/schema/domain validation | Processing after the external response |

The fixture implementation has **no** `webpage_http_round_trip` measurement.
No duration is assigned to the Grocery Store Website participant. Kroger
mode measures API HTTP requests instead; those intervals are not webpage
latency.
The experimental LLM attempt includes client-observed network transfer,
provider waiting, and SDK overhead; it does not expose provider-internal
execution time. The SDK retry count is zero.

## Innoslate traceability and limitations

Action names and IDs below are from the current `Recipe Roulette Export.xml`;
full traceability is in [docs/traceability.md](../traceability.md).

| Scenario/action | Verified model boundary | Current measurement relation |
|---|---|---|
| S.1 Webscraping — `I_293FF5YECAK8A_BDX2FTR813SDP` | Participants: User `I_3RKA1K727YKNZ_95TTAV7FWXJPM`, App `I_B0312FGXERG7B_BWY173TC0M5DY`, Grocery Store Website `I_9TDEK0SCJ8J4T_90DD1GZVR5P1F`. Actions S.1.1–S.1.8 and IDs are listed in `docs/traceability.md`. | Fixture timings are local analogues only. Kroger API request/JSON stages are the team-approved source substitution, not literal webpage requests/receipts or equivalent S.1 timing. The API participant is absent from the current model export. |
| S.2 Database — `I_F1H8BF80Z8GJC_8FGHTP2SG9K2S` | Participants: User `I_3RKA1K727YKNZ_95TTAV7FWXJPM`, App `I_B0312FGXERG7B_BWY173TC0M5DY`, Database `I_24D51EK49RKVC_BJHJFM0C6EY5P`; S.2.2 lookup is `I_D1TWDBN3V4KDD_8STG5Q336F9B4`. | `in_memory_lookup` is only a local dictionary analogue of a lookup operation, not a database or database-latency measurement. |
| S.3 LLM Pricing | No S.3 action sequence, action identifier, or S.3 participant allocation is present in the inspected export. | Experimental benchmark only; not a verified S.3 trace. |

The in-memory measurement is a limited local proxy against S.2, not a
database comparison. Fixture HTML parsing does not represent live S.1
request/receipt, page structure, store latency, or retailer pricing. Kroger
API timing may be compared with S.1 only as a clearly labeled team-selected
source substitution, not as literal webpage-scraping performance. Simulation
means and application measurements remain separately labeled; no actual S.3
simulation values are supplied.

Before a live Kroger run, verify the registered credentials, selected
location, current acceptable-use rules, and API quota guidance. Obtain the
team's explicit run approval and use the request cap. Update Innoslate to
reflect the Kroger API participant/sequence; no live webpage timing is
measured by this adapter.

## Simulation reference data

`results/chapter10-4/innoslate_reference.csv` contains the team-provided
10-run summaries: S.1 minimum 4.05 s, maximum 30.96 s, average 17.185 s; S.2
minimum 2.67 s, maximum 17.94 s, average 6.86 s. Median and standard
deviation were not provided and remain blank. S.3 is pending with no numeric
values.

## CSV format and analysis

`scripts/benchmark_pricing.py` writes one row per completed stage:

| Column | Description |
|---|---|
| `run_id` | Unique UUID for the benchmark run |
| `timestamp_utc` | Run start timestamp |
| `scenario`, `mode` | `actual_in_memory_dictionary` / `local`, `actual_html_fixture_pricing` / `html_fixture`, `actual_kroger_api_pricing` / `kroger`, or `experimental_llm_pricing` / `llm` |
| `model` | Configured `OPENAI_MODEL` for LLM runs; blank for grocery modes |
| `input_dataset_id` | Fixed benchmark input-set identifier; ingredient contents are not logged |
| `stage`, `duration_ns` | Stage label and monotonic elapsed nanoseconds |
| `status`, `run_status` | Stage and overall run status (`success` or `failure`) |
| `attempt_number`, `attempt_count`, `retry_attempts`, `provider_request_count` | Attempt index, retry total, and external request count |
| `error_type`, `provider_status_code` | Sanitized failure category / HTTP status; no raw exception or request text |

Existing Chapter 10 and Chapter 11 CSV files are not rewritten. In particular,
historical rows may use the earlier `pricing_request_processing` stage name;
new runs emit `pricing_request_preparation`.

The analyzer writes `stage-summary.csv` and `scenario-comparison.csv` only to
a new output directory; it refuses to overwrite existing files. Summaries
group by scenario, input dataset, stage, and status. They calculate minimum,
maximum, arithmetic mean, median, and sample standard deviation; standard
deviation is blank for fewer than two observations. Only successful
`pricing_workflow_total` rows populate measured-scenario summaries. Fixture
comparisons to S.1 remain blank; Kroger API measurements may be displayed
against S.1 only as a clearly labeled source substitution, not equivalent
webpage latency.

## Collection procedure

### Local in-memory pricing (30 runs)

From the repository root:

```powershell
python -m scripts.benchmark_pricing --mode local --runs 30 --max-requests 30
```

This makes 30 sequential calls to the in-process dictionary and Python pricing
functions. It does not invoke recipe generation, Flask, OpenAI, a browser, a
database, or a scraper.

### Local HTML fixture pricing (30 runs)

Choose a new output filename for each invocation:

```powershell
python -m scripts.benchmark_pricing --mode html-fixture --runs 30 --output results/chapter11/html-fixture-30.csv
```

This parses saved local HTML fixtures using the fixed five-ingredient basket.
It requires no `--live` flag, sends no requests, and does not measure retailer
HTTP latency. The script refuses to overwrite an existing CSV.

### Kroger Products API pricing (up to 30 workflows)

After separate approval for live requests, configure the three server-side
`KROGER_*` variables and choose a new output filename:

```powershell
python -m scripts.benchmark_pricing --mode kroger --live --runs 30 --max-requests 180 --output results\chapter11\kroger-api-30.csv
```

The fixed basket has five distinct searches. Each workflow uses a new client,
so its maximum is one token request plus five product searches: six per run,
180 for 30 runs. The request budget is enforced before each network request;
there are no retries, and the benchmark requires typing
`RUN 30 KROGER PRICING RUNS WITH CAP 180`. It stops on the first failure.
This command was not run during implementation.

### Experimental live LLM pricing (up to 30 requests)

Live LLM pricing is a separate, optional experiment. Configure the
server-side `OPENAI_API_KEY` and optionally `OPENAI_MODEL`; review the
selected model/account's current pricing before running:

```powershell
python -m scripts.benchmark_pricing --mode llm --live --runs 30 --max-requests 30 --output results/chapter10-4/llm-pricing-30.csv
```

This requires explicit `--live`, a per-invocation cap of 1–30 that is at least
the requested run count, and an interactive confirmation. It refuses to
overwrite an existing output, disables SDK retries, stops after the first
failed live run by default, and records the partial CSV. Use
`--continue-on-error` only when additional paid requests are separately
approved. No paid request is made by imports, tests, or local benchmark modes.

### Live grocery webpage pricing

There is no live HTML scraping mode. Kroger API runs are measured separately
and must not be reported as webpage scraping. `html_live` remains disabled.

## Verification expectations

Automated tests use saved local HTML fixtures, mocked Kroger HTTP responses,
and fake OpenAI clients. They cover timing capture, CSV fields, summary
statistics, product matching, package/unit normalization, pricing failures,
LLM structured output, failure sanitization, zero SDK retries, explicit live
opt-in, cancellation, and preservation of v1/v2 and deterministic stub
behavior.
