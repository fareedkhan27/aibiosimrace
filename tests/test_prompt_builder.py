import pytest
from arena.prompt_builder import build_race_prompt


def test_prompt_contains_brand():
    prompt = build_race_prompt(brand="Opdivo")
    assert "Opdivo" in prompt


def test_prompt_has_json_schema_fields():
    prompt = build_race_prompt(brand="Opdivo")
    for field in ['"pipeline"', '"probability"', '"trial_id"', '"est_launch"', '"provenance"', '"ai_insight"']:
        assert field in prompt, f"Missing field: {field}"


def test_prompt_has_calibration_rules():
    prompt = build_race_prompt(brand="Opdivo")
    assert "Phase III=35-90%" in prompt


def test_cee_region_modifier():
    prompt = build_race_prompt(brand="Opdivo", region="CEE")
    assert "REGION FOCUS" in prompt
    assert "Central and Eastern" in prompt


def test_latam_region_modifier():
    prompt = build_race_prompt(brand="Opdivo", region="LATAM")
    assert "ANVISA" in prompt


def test_mea_region_modifier():
    prompt = build_race_prompt(brand="Opdivo", region="MEA")
    assert "GCC" in prompt


def test_apac_region_modifier():
    prompt = build_race_prompt(brand="Opdivo", region="APAC")
    assert "PMDA" in prompt


def test_empty_region_no_modifier():
    prompt = build_race_prompt(brand="Opdivo", region="")
    assert "REGION FOCUS" not in prompt


def test_molecule_hint_injected():
    prompt = build_race_prompt(brand="Opdivo", molecule="nivolumab")
    assert "nivolumab" in prompt


def test_no_molecule_no_hint():
    prompt = build_race_prompt(brand="Opdivo", molecule="")
    assert "(INN:" not in prompt


def test_region_case_insensitive():
    prompt_lower = build_race_prompt(brand="X", region="cee")
    prompt_upper = build_race_prompt(brand="X", region="CEE")
    assert "Central and Eastern" in prompt_lower
    assert prompt_lower == prompt_upper
