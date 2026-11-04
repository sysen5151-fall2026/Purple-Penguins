# README for SYSEN5151 Semester Project

## Project Name - Recipe Roulette
### Team Members - Zachary Adornato, Jacob Brown, Ethan Gates, Stephen Gyurits

## Operational Concept
Meal planning is a time-consuming laborious process that everyone deals with. Dietary constraints and budget can complicate recipe selection and make the process even more difficult. The Recipe Roulette app is a system that generates relevant recipes while keeping budget, dietary restrictions, budget, and preferences in mind. 

Individuals that struggle with the previously mentioned constraints are the primary audience to experience meal planning issues. Existing meal planning leads to a non-nutritional diet, improper budgeting, and meals that take longer to shop for than they do to cook. There is a clear difficulty in balancing: cost, dietary restrictions, and preferences while maintaining a nutritional and healthy diet.

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