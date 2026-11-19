# README for SYSEN5151 Semester Project

## Project Name - Recipe Roulette
### Team Members - Zachary Adornato, Jacob Brown, Ethan Gates, Stephen Gyurits

## Operational Concept
Meal planning is a time-consuming laborious process that everyone deals with. Dietary constraints and budget can complicate recipe selection and make the process even more difficult. The Recipe Roulette app is a system that generates relevant recipes while keeping budget, dietary restrictions, budget, and preferences in mind. 

Individuals that struggle with the previously mentioned constraints are the primary audience to experience meal planning issues. Existing meal planning leads to a non-nutritional diet, improper budgeting, and meals that take longer to shop for than they do to cook. There is a clear difficulty in balancing: cost, dietary restrictions, and preferences while maintaining a nutritional and healthy diet.

<p align="center">
<img src="OPSCON_img.png" alt="Diagram" width="500">
</p>

## Development Setup

The project targets Python 3.12. From the repository root, create and activate a virtual environment, then install the project dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the Flask Foundation

Start the web application in its default deterministic recipe-stub mode:

```powershell
python -m app
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser. Grocery prices remain fixed demonstration estimates in both generation modes.

### Optional OpenAI recipe generation

The default `RECIPE_GENERATION_MODE=stub` requires no account or API key. To enable live recipe generation, create an OpenAI API project/key with billing enabled, then set the variables in the server's environment before starting the application. In PowerShell:

```powershell
$env:RECIPE_GENERATION_MODE = "openai"
$env:OPENAI_API_KEY = "<your-server-side-api-key>"
$env:OPENAI_MODEL = "gpt-6-luna"
python -m app
```

Keep the key in the process environment; do not put it in source files or browser code. `.env` files are ignored and are not loaded by the application. OpenAI usage can incur charges, including on retries; check current provider pricing. The application does not enforce a cumulative spend limit or cache generated recommendations. Ingredients, budget, and dietary restrictions are sent to OpenAI in live mode. Recipe generation is not guaranteed to enforce dietary restrictions; verify ingredients and allergens yourself. The modeled login prerequisite remains simulated and does not authenticate users.

Set `$env:RECIPE_GENERATION_MODE = "stub"` to return to the deterministic local recipes.

## Run the Console Walking Skeleton

The original interactive console workflow remains available explicitly:

```powershell
python -m app --cli
```

## Run Automated Tests

Run the test suite from the repository root:

```powershell
python -m pytest
```

## Chapter 10.4 Pricing Benchmarks

The local benchmark measures the existing in-memory ingredient-price lookup
and Python processing using the same fixed ingredient names as the isolated
LLM pricing experiment. It does not execute recipe generation, browser input,
web scraping, or a database query.

Run 30 local measurements:

```powershell
python -m scripts.benchmark_pricing --mode local --runs 30 --max-requests 30
```

LLM pricing is experimental and returns unverified estimates, not store
prices. It is isolated from Recipe Roulette's production recipe/pricing path.
Live requests require `--mode llm --live`, an explicit per-invocation cap, and
typing the confirmation phrase. The SDK retry count is zero, so a 30-run
benchmark sends at most 30 API requests. Each request may incur charges.

After separately reviewing and approving the live experiment, configure
`OPENAI_API_KEY` and, optionally, `OPENAI_MODEL` in the process environment,
then run:

```powershell
python -m scripts.benchmark_pricing --mode llm --live --runs 30 --max-requests 30 --output results/chapter10-4/llm-pricing-30.csv
```

The benchmark refuses to overwrite a result CSV. Its output path is printed
after each run; local and live timings use nanoseconds and include per-stage
status and retry counts. Summarize and compare one or more result files with
the team-provided Innoslate simulation reference:

```powershell
$localCsv = Get-ChildItem results\chapter10-4\local-*.csv |
  Sort-Object LastWriteTime |
  Select-Object -Last 1 -ExpandProperty FullName
python -m scripts.analyze_pricing_benchmark --input $localCsv
```

See [the Chapter 10.4 methodology](docs/performance/chapter10-4-methodology.md)
for modeled action traceability, CSV columns, simulation values, and comparison
limitations. The current XML export contains no S.3 pricing sequence; do not
treat the experimental LLM run as an implemented or simulated S.3 scenario.