# Environment 
Language / version: Python 3.12  
Runtime:            local, virtual environment  
Model runner:       VS Code AI
Model:              GPT-5 mini
Editor:             VS Code  
Assistants in use:  All - ChatGPT, Z. Adornato - VS Code AI

## Optional OpenAI recipe-generation configuration

Recipe generation defaults to the local deterministic stub. To use the OpenAI API, configure these variables in the server process environment:

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `RECIPE_GENERATION_MODE` | No | `stub` | Select `stub` or `openai`. |
| `OPENAI_API_KEY` | For `openai` mode | None | Server-side API credential. Never place it in frontend code or commit it. |
| `OPENAI_MODEL` | No | `gpt-6-luna` | OpenAI model used for structured recipe generation and price estimation. |
| `OPENAI_TIMEOUT_SECONDS` | No | `30` | Per-attempt timeout; accepted range is greater than 0 and at most 120 seconds. |

The application does not load `.env` files. `.env` files are ignored by Git; configure secrets through the operating system, deployment platform, or a secret manager. OpenAI recipe generation sends ingredients, budget, and dietary restrictions to OpenAI. When both store and ZIP code are supplied, a separate OpenAI request estimates ingredient prices and receives the generated ingredient names plus the selected store and ZIP code. Recipe generation has a maximum of ten total attempts for transient failures; price estimation does not retry. The integration does not enforce an application-wide spend limit or cache recommendations.

In `stub` mode, grocery pricing remains deterministic, uses the local demonstration dictionary, and ignores store/ZIP inputs. In `openai` mode with store and ZIP context, the application returns approximate, unverified model estimates—not live prices, inventory, or package quotes. OpenAI mode without store/ZIP context retains demonstration pricing for backward compatibility. Unknown names in demonstration mode use the existing `$1.00` fallback.