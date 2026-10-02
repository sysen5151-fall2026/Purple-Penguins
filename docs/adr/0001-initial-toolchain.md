# ADR 0001 — Initial toolchain

- Date: 2026-10-02
- Status: accepted

Context
:
The project documentation (`docs/environment.md`) identifies the runtime environment and tools available to the team for Chapter 1.

Decision
:
- Use Python 3.12 as the documented runtime for development and testing.
- Use a local virtual environment (venv) for isolation.
- Use VS Code as the primary editor. The project may be assisted by the VS Code AI model runner (documented in `docs/environment.md`).
- Keep `requirements.txt` as a manifest placeholder for Chapter 1; do not add runtime dependencies unless required by later chapters.

Consequences
:
- Repository remains a Chapter-1 scaffold without added frameworks or runtime packages.
- Future decisions about LLM models, framework choices, or external services will be recorded in follow-up ADRs.
