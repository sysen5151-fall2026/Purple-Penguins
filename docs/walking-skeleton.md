# Walking Skeleton — Chapter 2

## Primary Use Case

UC.1 — User requests the app generates a list of recipes with prices (Baseline Scenario)

## Purpose

This document records the call sequence for the primary baseline scenario. It will be used to implement the walking skeleton in Chapter 2.

## Participants

- User
- App
- LLM API
- Grocery Store

## Call Sequence

1. User → App: Open App
2. App → User: Request Login Info
3. User → App: Provide Login Info
4. App → User: Approve Login
5. App → User: Request Ingredients
6. User → App: Provide Ingredients
7. App → User: Request Budget
8. User → App: Provide Budget
9. App → User: Request Dietary Restrictions
10. User → App: Provide Dietary Restrictions
11. App → LLM API: Send Recipe Requirements
12. LLM API → App: Generate Recipes
13. App → LLM API: Request Pricing
14. LLM API → Grocery Store: Retrieve Prices
15. Grocery Store → LLM API: Provide Pricing
16. LLM API → App: Process Ingredient Pricing
17. App → User: Display Recipe & Pricing

## Notes

- This is documentation only; no implementation is included at this stage.
- The sequence diagram is the authoritative source for interaction order and participant names.
- Implementation of the walking skeleton will follow in Chapter 2, guided by this call sequence.