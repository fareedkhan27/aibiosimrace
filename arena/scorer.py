import re
from collections import Counter
from datetime import datetime

SCORE_CONFIG = {
    "developer_pts":   12, "developer_max":  84,
    "provenance_pts":   8, "provenance_max": 40,
    "launch_q_pts":     6, "launch_max":     30,
    "trial_id_pts":     7, "trial_id_max":   35,
    "patent_pts":      10,
    "competitor_pts":   3, "competitor_max": 15,
    "insight_pts":     10,
    "speed_bonuses":  [10, 5, 2, 0, 0],
    "calib_penalty":  20,
}

CALIBRATION = {
    "phase iii":   (35, 90),
    "phase ii":    (10, 40),
    "phase i":     (0,  10),
    "preclinical": (0,  10),
    "approved":    (55, 85),
    "launched":    (40, 80),
}


def _score_one(data: dict | None) -> dict:
    if not data or not data.get("pipeline"):
        empty_bd = {
            "developers": 0, "provenance": 0, "launches": 0,
            "trial_ids": 0, "patent": 0, "competitors": 0,
            "insight": 0, "speed": 0,
        }
        return {"total": 0, "bd": empty_bd, "penalized": 0}

    c    = SCORE_CONFIG
    pipe = data.get("pipeline", [])
    bd   = {}

    bd["developers"] = min(len(pipe) * c["developer_pts"], c["developer_max"])
    bd["provenance"] = min(len(data.get("provenance", [])) * c["provenance_pts"], c["provenance_max"])

    q_yr = sum(
        1 for p in pipe
        if p.get("est_launch") and re.match(r"^[QH][1-4]\s*\d{4}", p["est_launch"] or "")
    )
    bd["launches"]    = min(q_yr * c["launch_q_pts"], c["launch_max"])

    has_id = sum(
        1 for p in pipe
        if p.get("trial_id") and p["trial_id"] not in (None, "null", "")
    )
    bd["trial_ids"]   = min(has_id * c["trial_id_pts"], c["trial_id_max"])
    bd["patent"]      = c["patent_pts"] if (data.get("patent_expiry") and data["patent_expiry"] not in (None, "null", "")) else 0
    bd["competitors"] = min(len(data.get("competitors", [])) * c["competitor_pts"], c["competitor_max"])
    bd["insight"]     = c["insight_pts"] if len(data.get("ai_insight", "")) > 60 else 0
    bd["speed"]       = 0

    penalty = 0
    for p in pipe:
        phase = (p.get("phase") or "").lower()
        band  = None
        for key, rng in CALIBRATION.items():
            if key in phase:
                band = rng
                break
        if band:
            try:
                prob = int(p.get("probability", 0))
            except (TypeError, ValueError):
                prob = 0
            if (prob < band[0] or prob > band[1]) and len(p.get("note", "")) <= 20:
                penalty += c["calib_penalty"]

    total = sum(bd.values()) - penalty
    return {"total": max(total, 0), "bd": bd, "penalized": penalty}


def score_and_declare_winner(normalized: list[dict]) -> dict:
    scored = []
    for r in normalized:
        sc = _score_one(r.get("output"))
        scored.append({**r, "score": sc})

    by_speed = sorted(scored, key=lambda x: x.get("elapsed", 99))
    for i, r in enumerate(by_speed):
        bonus = SCORE_CONFIG["speed_bonuses"][i] if i < len(SCORE_CONFIG["speed_bonuses"]) else 0
        r["score"]["bd"]["speed"] = bonus
        r["score"]["total"]      += bonus

    winner = max(scored, key=lambda x: x["score"]["total"], default=None)
    ranked = sorted(scored, key=lambda x: x["score"]["total"], reverse=True)

    return {
        "winner":        winner["model_key"] if winner else None,
        "winner_score":  winner["score"]["total"] if winner else 0,
        "winner_data":   winner.get("output") if winner else None,
        "rankings": [
            {
                "model_key": r["model_key"],
                "score":     r["score"],
                "output":    r.get("output"),
                "elapsed":   r.get("elapsed"),
                "error":     r.get("error"),
            }
            for r in ranked
        ],
        "consensus":     _check_consensus(scored),
        "extraction_ts": datetime.utcnow().isoformat(),
    }


def _check_consensus(scored: list[dict]) -> bool:
    companies = [
        (r.get("output") or {}).get("pipeline", [{}])[0].get("company", "").lower()
        for r in scored
        if (r.get("output") or {}).get("pipeline")
    ]
    if len(companies) < 2:
        return False
    top = Counter(companies).most_common(1)
    return top[0][1] >= 2 if top else False
