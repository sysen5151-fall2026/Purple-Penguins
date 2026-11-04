import pytest


@pytest.fixture(autouse=True)
def use_stub_recipe_generation_by_default(monkeypatch):
    monkeypatch.setenv("RECIPE_GENERATION_MODE", "stub")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
