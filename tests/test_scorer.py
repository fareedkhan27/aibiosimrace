import pytest
from arena.scorer import _score_one, score_and_declare_winner

SAMPLE = {
    "brand": "Opdivo",
    "inn": "nivolumab",
    "patent_expiry": "2028-03",
    "competitors": ["Keytruda (MSD)", "Tecentriq (Roche)"],
    "pipeline": [
        {
            "company": "Celltrion",
            "indications": ["NSCLC", "Melanoma"],
            "phase": "Phase III",
            "trial_id": "NCT04500000",
            "est_launch": "Q2 2026",
            "markets": ["KR", "EU"],
            "probability": 65,
            "source": "ClinicalTrials",
            "note": "Phase III complete; BLA filing pending",
        },
        {
            "company": "Samsung Bioepis",
            "indications": ["RCC"],
            "phase": "Phase II",
            "trial_id": None,
            "est_launch": None,
            "markets": ["KR"],
            "probability": 25,
            "source": "Company",
            "note": "Phase II initiated Q3 2024",
        },
    ],
    "provenance": [
        "ClinicalTrials.gov NCT04500000",
        "Samsung Bioepis investor report Q4 2024",
    ],
    "ai_insight": (
        "Celltrion's Phase III completion combined with existing commercial "
        "infrastructure in EU represents the highest near-term launch risk."
    ),
    "confidence": "Moderate",
}


def test_developers():
    result = _score_one(SAMPLE)
    assert result["bd"]["developers"] == 24  # 2 × 12


def test_provenance():
    result = _score_one(SAMPLE)
    assert result["bd"]["provenance"] == 16  # 2 × 8


def test_launch_qyear():
    result = _score_one(SAMPLE)
    assert result["bd"]["launches"] == 6  # 1 Q+Year × 6


def test_trial_ids():
    result = _score_one(SAMPLE)
    assert result["bd"]["trial_ids"] == 7  # 1 trial ID × 7


def test_patent():
    result = _score_one(SAMPLE)
    assert result["bd"]["patent"] == 10


def test_calibration_clean():
    result = _score_one(SAMPLE)
    assert result["penalized"] == 0


def test_calibration_penalty_fires():
    bad = {
        **SAMPLE,
        "pipeline": [{**SAMPLE["pipeline"][0], "probability": 5, "note": ""}],
    }
    result = _score_one(bad)
    assert result["penalized"] == 20  # Phase III prob=5, below floor 35


def test_empty_pipeline():
    result = _score_one({**SAMPLE, "pipeline": []})
    assert result["bd"]["developers"] == 0


def test_none_data():
    result = _score_one(None)
    assert result["total"] == 0


def test_winner_declared():
    results = [
        {"model_key": "analyst", "output": SAMPLE, "elapsed": 2.1, "error": None},
        {"model_key": "hunter",  "output": None,   "elapsed": 1.5, "error": "timeout"},
    ]
    outcome = score_and_declare_winner(results)
    assert outcome["winner"] == "analyst"


def test_speed_bonus_applied():
    results = [
        {"model_key": "analyst", "output": SAMPLE, "elapsed": 2.1, "error": None},
        {"model_key": "scanner", "output": SAMPLE, "elapsed": 4.0, "error": None},
    ]
    outcome = score_and_declare_winner(results)
    analyst = next(r for r in outcome["rankings"] if r["model_key"] == "analyst")
    scanner = next(r for r in outcome["rankings"] if r["model_key"] == "scanner")
    assert analyst["score"]["bd"]["speed"] == 10
    assert scanner["score"]["bd"]["speed"] == 5


def test_consensus_flag():
    results = [
        {"model_key": "analyst", "output": SAMPLE, "elapsed": 2.1, "error": None},
        {"model_key": "scanner", "output": SAMPLE, "elapsed": 3.0, "error": None},
    ]
    outcome = score_and_declare_winner(results)
    assert outcome["consensus"] is True


def test_rankings_ordered_by_score():
    low_output = {**SAMPLE, "pipeline": [], "provenance": []}
    results = [
        {"model_key": "analyst", "output": SAMPLE,      "elapsed": 2.0, "error": None},
        {"model_key": "hunter",  "output": low_output,  "elapsed": 1.0, "error": None},
    ]
    outcome = score_and_declare_winner(results)
    scores = [r["score"]["total"] for r in outcome["rankings"]]
    assert scores == sorted(scores, reverse=True)
