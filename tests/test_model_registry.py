import pytest
from arena.model_registry import MODEL_REGISTRY, OPENROUTER_MODELS

REQUIRED_KEYS = {"or_id", "label", "alias", "color", "specialty", "cost_tier", "system"}
EXPECTED_MODELS = {"analyst", "hunter", "scanner", "strategist", "challenger"}


def test_all_five_models_present():
    assert set(MODEL_REGISTRY.keys()) == EXPECTED_MODELS


def test_all_models_have_required_fields():
    for key, meta in MODEL_REGISTRY.items():
        missing = REQUIRED_KEYS - set(meta.keys())
        assert not missing, f"Model '{key}' missing fields: {missing}"


def test_all_systems_nonempty():
    for key, meta in MODEL_REGISTRY.items():
        assert len(meta["system"]) > 50, f"Model '{key}' system prompt too short"


def test_openrouter_models_set():
    assert len(OPENROUTER_MODELS) == 5
    for or_id in OPENROUTER_MODELS:
        assert "/" in or_id, f"Invalid OpenRouter ID format: {or_id}"


def test_colors_are_hex():
    for key, meta in MODEL_REGISTRY.items():
        assert meta["color"].startswith("#"), f"Model '{key}' color not hex"


def test_cost_tiers_valid():
    valid_tiers = {"high", "medium", "low"}
    for key, meta in MODEL_REGISTRY.items():
        assert meta["cost_tier"] in valid_tiers, f"Model '{key}' invalid cost_tier"


def test_specific_openrouter_ids():
    assert MODEL_REGISTRY["analyst"]["or_id"] == "anthropic/claude-sonnet-4-5"
    assert MODEL_REGISTRY["hunter"]["or_id"] == "openai/gpt-4o"
    assert MODEL_REGISTRY["scanner"]["or_id"] == "google/gemini-2.0-flash-001"
    assert MODEL_REGISTRY["strategist"]["or_id"] == "mistralai/mistral-large"
    assert MODEL_REGISTRY["challenger"]["or_id"] == "meta-llama/llama-3.1-70b-instruct"
