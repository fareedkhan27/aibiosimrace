"""
tests/test_normalizer.py
Unit tests for arena/normalizer.py — no network required.
"""

import pytest
from arena.normalizer import (
    normalize_inn,
    normalize_date,
    clamp_probability,
    normalize_outputs,
)


# ── INN normalization ─────────────────────────────────────────────────────────

def test_inn_exact_match():
    assert normalize_inn("nivolumab") == "nivolumab"


def test_inn_fuzzy_typo():
    # Common misspelling — should still match
    result = normalize_inn("nivolumabb")
    assert result == "nivolumab"


def test_inn_case_insensitive():
    assert normalize_inn("Adalimumab") == "adalimumab"


def test_inn_no_match_returns_original():
    # Completely unrelated string — returned unchanged
    original = "xyznosuchdrug"
    result = normalize_inn(original)
    assert result == original


def test_inn_none_returns_none():
    assert normalize_inn(None) is None


def test_inn_empty_returns_empty():
    assert normalize_inn("") == ""


def test_inn_known_inn_rituximab():
    assert normalize_inn("rituximab") == "rituximab"


# ── Date normalization ────────────────────────────────────────────────────────

def test_date_yyyy_mm_q1():
    assert normalize_date("2026-01") == "Q1 2026"


def test_date_yyyy_mm_q2():
    assert normalize_date("2026-04") == "Q2 2026"


def test_date_yyyy_mm_q3():
    assert normalize_date("2026-07") == "Q3 2026"


def test_date_yyyy_mm_q4():
    assert normalize_date("2026-10") == "Q4 2026"


def test_date_already_q_year():
    assert normalize_date("Q2 2026") == "Q2 2026"


def test_date_already_h_year():
    assert normalize_date("H1 2027") == "H1 2027"


def test_date_year_only():
    assert normalize_date("2027") == "2027"


def test_date_none_returns_none():
    assert normalize_date(None) is None


def test_date_empty_returns_none():
    assert normalize_date("") is None


def test_date_q_year_variant_dash():
    # "Q2-2026" should normalise to "Q2 2026"
    result = normalize_date("Q2-2026")
    assert result == "Q2 2026"


def test_date_uppercase_preserved():
    result = normalize_date("Q3 2025")
    assert result == "Q3 2025"


# ── Probability clamping ──────────────────────────────────────────────────────

def test_clamp_phase_iii_within_band():
    assert clamp_probability(65, "Phase III") == 65


def test_clamp_phase_iii_below_floor():
    # Floor for Phase III is 35
    assert clamp_probability(5, "Phase III") == 35


def test_clamp_phase_iii_above_ceiling():
    # Ceiling for Phase III is 90
    assert clamp_probability(95, "Phase III") == 90


def test_clamp_phase_ii_within_band():
    assert clamp_probability(25, "Phase II") == 25


def test_clamp_phase_ii_below_floor():
    assert clamp_probability(5, "Phase II") == 10


def test_clamp_phase_i_above_ceiling():
    # Ceiling for Phase I is 10
    assert clamp_probability(50, "Phase I") == 10


def test_clamp_approved_within_band():
    assert clamp_probability(70, "Approved") == 70


def test_clamp_launched_below_floor():
    assert clamp_probability(20, "Launched") == 40


def test_clamp_unknown_phase_unchanged():
    # No calibration band → unchanged
    assert clamp_probability(99, "Regulatory Review") == 99


def test_clamp_none_probability():
    assert clamp_probability(None, "Phase III") is None


def test_clamp_no_phase():
    assert clamp_probability(50, None) == 50


# ── normalize_outputs integration ────────────────────────────────────────────

_SAMPLE_RESULT = {
    "model_key": "analyst",
    "or_id": "anthropic/claude-sonnet-4-5",
    "elapsed": 3.2,
    "error": None,
    "output": {
        "brand": "Opdivo",
        "inn": "nivolumab",
        "patent_expiry": "2028-03",
        "competitors": ["Keytruda (MSD)"],
        "pipeline": [
            {
                "company": "Celltrion",
                "indications": ["NSCLC"],
                "phase": "Phase III",
                "trial_id": "NCT04500000",
                "est_launch": "2026-06",   # should become Q2 2026
                "markets": ["EU"],
                "probability": 95,          # should be clamped to 90
                "source": "ClinicalTrials",
                "note": "Phase III complete",
            },
            {
                "company": "Samsung Bioepis",
                "indications": ["RCC"],
                "phase": "Phase II",
                "trial_id": None,
                "est_launch": None,
                "markets": ["KR"],
                "probability": 5,           # should be clamped to 10 (Phase II floor)
                "source": "Company",
                "note": "Phase II initiated",
            },
        ],
        "provenance": ["ClinicalTrials.gov"],
        "ai_insight": "Test insight",
        "confidence": "Moderate",
    },
}


def test_normalize_outputs_returns_list():
    results = normalize_outputs([_SAMPLE_RESULT])
    assert isinstance(results, list)
    assert len(results) == 1


def test_normalize_outputs_date_conversion():
    results = normalize_outputs([_SAMPLE_RESULT])
    pipeline = results[0]["output"]["pipeline"]
    assert pipeline[0]["est_launch"] == "Q2 2026"


def test_normalize_outputs_probability_clamped_ceiling():
    results = normalize_outputs([_SAMPLE_RESULT])
    pipeline = results[0]["output"]["pipeline"]
    assert pipeline[0]["probability"] == 90  # 95 clamped to Phase III ceiling


def test_normalize_outputs_probability_clamped_floor():
    results = normalize_outputs([_SAMPLE_RESULT])
    pipeline = results[0]["output"]["pipeline"]
    assert pipeline[1]["probability"] == 10  # 5 clamped to Phase II floor


def test_normalize_outputs_inn_preserved():
    results = normalize_outputs([_SAMPLE_RESULT])
    assert results[0]["output"]["inn"] == "nivolumab"


def test_normalize_outputs_null_output_passthrough():
    null_result = {
        "model_key": "hunter",
        "or_id": "openai/gpt-4o",
        "elapsed": 1.0,
        "error": "timeout",
        "output": None,
    }
    results = normalize_outputs([null_result])
    assert results[0]["output"] is None
    assert results[0]["error"] == "timeout"


def test_normalize_outputs_does_not_mutate_input():
    import copy
    original = copy.deepcopy(_SAMPLE_RESULT)
    normalize_outputs([_SAMPLE_RESULT])
    # Original probability should be unchanged
    assert _SAMPLE_RESULT["output"]["pipeline"][0]["probability"] == 95


def test_normalize_outputs_none_launch_stays_none():
    results = normalize_outputs([_SAMPLE_RESULT])
    pipeline = results[0]["output"]["pipeline"]
    assert pipeline[1]["est_launch"] is None
