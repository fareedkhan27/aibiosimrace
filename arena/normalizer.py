"""
arena/normalizer.py
-------------------
Post-processing for raw LLM race outputs:
  1. INN standardization — fuzzy-match company/molecule names to a canonical list
  2. Date → Q+Year normalization — "2026-04" → "Q2 2026", "H1 2027" → "H1 2027", etc.
  3. Probability clamping — enforce per-phase calibration bands
"""

import re
from typing import Optional

from rapidfuzz import process, fuzz

# ── INN canonical list ────────────────────────────────────────────────────────
# Common biosimilar INNs + originator brand cross-references.
# Extend as needed; fuzzy match handles typos / alternate spellings.
CANONICAL_INNS: list[str] = [
    "adalimumab",
    "bevacizumab",
    "certolizumab pegol",
    "denosumab",
    "epoetin alfa",
    "etanercept",
    "filgrastim",
    "infliximab",
    "insulin glargine",
    "natalizumab",
    "nivolumab",
    "pembrolizumab",
    "pertuzumab",
    "ranibizumab",
    "rituximab",
    "teriparatide",
    "tocilizumab",
    "trastuzumab",
    "ustekinumab",
    "vedolizumab",
]

# Minimum similarity score (0-100) to accept a fuzzy INN match
_INN_THRESHOLD = 80

# ── Calibration bands (phase keyword → (min%, max%)) ─────────────────────────
_CALIBRATION: dict[str, tuple[int, int]] = {
    "phase iii":  (35, 90),
    "phase ii":   (10, 40),
    "phase i":    (0, 10),
    "preclinical": (0, 10),
    "approved":   (55, 85),
    "launched":   (40, 80),
}


# ── INN normalization ─────────────────────────────────────────────────────────

def normalize_inn(raw: Optional[str]) -> Optional[str]:
    """
    Fuzzy-match *raw* against CANONICAL_INNS.
    Returns the canonical INN if similarity ≥ threshold, otherwise *raw* unchanged.
    """
    if not raw:
        return raw
    cleaned = raw.strip().lower()
    result = process.extractOne(
        cleaned,
        CANONICAL_INNS,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=_INN_THRESHOLD,
    )
    if result:
        return result[0]   # canonical form
    return raw


# ── Date normalization ────────────────────────────────────────────────────────
# Accepted input patterns → normalised Q+Year output
#   "2026-04"   → "Q2 2026"
#   "2026"      → "2026"        (year-only — kept as-is)
#   "Q2 2026"   → "Q2 2026"     (already normalised)
#   "H1 2027"   → "H1 2027"     (half-year — kept as-is; scorer also accepts H#)
#   "Q2-2026"   → "Q2 2026"     (variant separator)
#   "2026-Q2"   → "Q2 2026"     (reversed order)
#   None / ""   → None

_MONTH_TO_QUARTER = {
    1: 1, 2: 1, 3: 1,
    4: 2, 5: 2, 6: 2,
    7: 3, 8: 3, 9: 3,
    10: 4, 11: 4, 12: 4,
}

# Regex: already in Q# YYYY or H# YYYY form
_RE_ALREADY_NORMALISED = re.compile(r"^[QH][1-4]\s*\d{4}$", re.IGNORECASE)
# Regex: YYYY-MM
_RE_YYYY_MM = re.compile(r"^(\d{4})-(\d{2})$")
# Regex: YYYY-Q# or Q#-YYYY or Q# YYYY
_RE_Q_YEAR = re.compile(r"(?:(\d{4})[^\w])?[Qq]([1-4])(?:[^\w](\d{4}))?")
# Regex: plain year
_RE_YEAR_ONLY = re.compile(r"^\d{4}$")


def normalize_date(raw: Optional[str]) -> Optional[str]:
    """Convert various date string formats to Q+Year or keep as-is."""
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None

    # Already normalised: Q2 2026 / H1 2027
    if _RE_ALREADY_NORMALISED.match(s):
        # Normalise spacing: "Q2-2026" → "Q2 2026"
        normed = re.sub(r"([QHqh][1-4])[\s\-]+(\d{4})", lambda m: f"{m.group(1).upper()} {m.group(2)}", s)
        return normed if _RE_ALREADY_NORMALISED.match(normed) else s.upper().replace("-", " ")

    # YYYY-MM  → Q# YYYY
    m = _RE_YYYY_MM.match(s)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            q = _MONTH_TO_QUARTER[month]
            return f"Q{q} {year}"

    # Year-only
    if _RE_YEAR_ONLY.match(s):
        return s  # leave plain year intact

    # Q# YYYY or YYYY-Q# variants
    m = _RE_Q_YEAR.search(s)
    if m:
        year = m.group(1) or m.group(3)
        q = m.group(2)
        if year and q:
            return f"Q{q} {year}"

    # Fallback — return original
    return s


# ── Probability clamping ──────────────────────────────────────────────────────

def clamp_probability(probability: Optional[int], phase: Optional[str]) -> Optional[int]:
    """
    Clamp *probability* into the calibration band for the given *phase*.
    If no band is found for the phase, the value is returned unchanged.
    """
    if probability is None:
        return probability
    if not phase:
        return probability

    phase_lower = phase.lower()
    band: Optional[tuple[int, int]] = None
    for key, rng in _CALIBRATION.items():
        if key in phase_lower:
            band = rng
            break

    if band is None:
        return probability

    lo, hi = band
    return max(lo, min(hi, probability))


# ── Pipeline entry normalization ──────────────────────────────────────────────

def _normalize_pipeline_entry(entry: dict) -> dict:
    """Normalize a single pipeline entry in-place (returns new dict)."""
    e = dict(entry)

    # Normalize est_launch date
    e["est_launch"] = normalize_date(e.get("est_launch"))

    # Clamp probability
    prob = e.get("probability")
    if prob is not None:
        try:
            prob = int(prob)
        except (TypeError, ValueError):
            prob = None
    e["probability"] = clamp_probability(prob, e.get("phase"))

    return e


# ── Top-level normalize_outputs ───────────────────────────────────────────────

def normalize_outputs(raw_results: list[dict]) -> list[dict]:
    """
    Normalize a list of raw race results (as returned by arena/client.py).

    For each result that has a valid *output* dict:
      - Normalize the INN field
      - Normalize all pipeline entry dates and probabilities

    The *raw_results* list is not mutated; a new list is returned.
    """
    normalized = []
    for result in raw_results:
        r = dict(result)
        output = r.get("output")

        if isinstance(output, dict):
            out = dict(output)

            # INN normalization
            out["inn"] = normalize_inn(out.get("inn"))

            # Pipeline entry normalization
            pipeline = out.get("pipeline")
            if isinstance(pipeline, list):
                out["pipeline"] = [_normalize_pipeline_entry(p) for p in pipeline]

            r["output"] = out

        normalized.append(r)
    return normalized
