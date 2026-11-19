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
| `OPENAI_MODEL` | No | `gpt-6-luna` | OpenAI model used for structured recipe generation. |
| `OPENAI_TIMEOUT_SECONDS` | No | `30` | Per-attempt timeout; accepted range is greater than 0 and at most 120 seconds. |

The application does not load `.env` files. `.env` files are ignored by Git; configure secrets through the operating system, deployment platform, or a secret manager. Live mode sends user-provided ingredients, budget, and dietary restrictions to OpenAI. Recipe generation has a maximum of ten total attempts for transient failures. The integration does not enforce an application-wide spend limit or cache recommendations.

Grocery pricing remains deterministic in both modes. Unknown ingredient names use the existing `$1.00` fallback, so live-generated ingredient estimates may be inaccurate. Current API pricing and account/project setup are provider-managed and may change; verify them before enabling live mode.