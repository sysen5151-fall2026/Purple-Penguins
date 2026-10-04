# Prompt summary — Chapter 2 walking skeleton
The implementation plan is approved with the following corrections and constraints.

Proceed with implementation.

1. Use the existing repository structure only:
   - app.py
   - user_interface/
   - llm_api_interface/
   - grocery_store_interface/

2. Do NOT create separate stub-data files.
   Keep deterministic hard-coded recipe data inside llm_api_interface/__init__.py.
   Keep deterministic hard-coded pricing data inside grocery_store_interface/__init__.py.

3. app.py may serve as the minimal executable entry point/orchestrator for the walking skeleton.
   Do NOT interpret this as permission to create additional internal architecture.

4. Do NOT create:
   - service layers
   - controller layers
   - repository layers
   - backend packages
   - database layers
   - additional application modules
   - new participants
   - new actors

5. The User interface may use a minimal console-based interaction using Python's built-in input() and print(), but it must remain a thin stub/interface.
   Do NOT add a GUI framework, authentication system, input-validation framework, or other UI infrastructure.

6. The LLM API remains a stub.
   It must:
   - accept the recipe requirements
   - return deterministic hard-coded recipe data
   - accept the pricing request
   - call the Grocery Store stub
   - process the returned pricing data
   - return deterministic recipe-pricing data

7. The Grocery Store remains a stub.
   It must:
   - accept the recipe ingredient list
   - return deterministic hard-coded ingredient pricing
   - perform no real web access or scraping

8. The complete walking-skeleton path must be demonstrable:

   User
   → App
   → LLM API
   → Grocery Store
   → LLM API
   → App
   → User

9. Use docs/walking-skeleton.md as the authoritative call sequence.
   Do not modify the sequence, participants, or Innoslate model.

10. No real:
    - LLM API calls
    - web scraping
    - authentication
    - database access
    - external API calls

11. Do not add:
    - error handling
    - retries
    - logging
    - telemetry
    - unrelated features

12. Do not modify Chapter 1 documentation unless absolutely required for the walking skeleton to run.

13. Before implementation, confirm the exact file paths you will modify.
    They should be:
    - app.py
    - user_interface/__init__.py
    - llm_api_interface/__init__.py
    - grocery_store_interface/__init__.py

After implementation:
- show the complete contents of each modified file
- show the final repository tree
- explain how the implementation maps to the 17 calls in docs/walking-skeleton.md
- identify any files other than the four listed above that were changed
- do not commit or push yet