REGION_MODIFIERS = {
    "CEE": (
        "Focus on Central and Eastern European markets (Poland, Czech Republic, Hungary, "
        "Romania, Bulgaria, Baltic states). Note EMA biosimilar approval, national HA tender "
        "cycles, and biosimilar substitution policies per country."
    ),
    "LATAM": (
        "Focus on Latin American markets. Specifically: Brazil (ANVISA pathway, 6-18 month "
        "post-reference launch delays), Argentina (ANMAT), Colombia (INVIMA). "
        "Note local packaging and cold-chain requirements."
    ),
    "MEA": (
        "Focus on Middle East and Africa markets. Gulf Cooperation Council (GCC) tender "
        "cycles in Q1/Q3, WHO prequalification as positive signal for sub-Saharan Africa "
        "procurement, Saudi FDA and UAE MOHAP approvals."
    ),
    "APAC": (
        "Focus on Asia-Pacific markets: Japan (PMDA), Australia (TGA), China (NMPA separate "
        "biosimilar guideline), South Korea (MFDS). Note interchangeability and automatic "
        "substitution policies."
    ),
}

_JSON_SCHEMA = """{
  "brand": "brand name as given",
  "inn": "international nonproprietary name",
  "originator": "originator company name",
  "patent_expiry": "YYYY-MM or YYYY or estimated range or null",
  "mechanism": "one concise MOA sentence",
  "therapeutic_area": "oncology | immunology | etc",
  "competitors": ["reference biologic competitors — not biosimilars — name (company)"],
  "pipeline": [
    {
      "company": "developer company name",
      "indications": ["approved or targeted indications"],
      "phase": "Preclinical|Phase I|Phase II|Phase III|Approved|Launched",
      "trial_id": "NCT or CTIS ID or null",
      "est_trial_completion": "YYYY-MM or null",
      "est_launch": "Q# YYYY or YYYY or H# YYYY or null",
      "markets": ["country or region codes"],
      "probability": 55,
      "source": "ClinicalTrials|CTIS|EMA|FDA|WHO|Company|Press|Inferred",
      "note": "single most important competitive fact, max 90 chars"
    }
  ],
  "provenance": ["specific source names with detail"],
  "ai_insight": "one paragraph — what pattern or risk does this pipeline reveal that a human analyst might miss? be specific, cite data from the pipeline.",
  "confidence": "High|Moderate|Low"
}"""

_CALIBRATION_RULES = (
    "probability MUST respect calibration: "
    "Phase III=35-90%, Phase II=10-40%, Phase I=0-10%, "
    "Preclinical=0-10%, Approved=55-85%, Launched=40-80%"
)


def build_race_prompt(brand: str, region: str = "", molecule: str = "") -> str:
    inn_hint = f" (INN: {molecule})" if molecule else ""
    region_key = region.upper()
    region_block = (
        f"\n\nREGION FOCUS: {REGION_MODIFIERS[region_key]}"
        if region_key in REGION_MODIFIERS
        else ""
    )
    return (
        f'Extract comprehensive biosimilar competitive intelligence for the reference biologic: '
        f'"{brand}"{inn_hint}{region_block}\n\n'
        f"Return ONLY a single valid JSON object with this exact structure:\n"
        f"{_JSON_SCHEMA}\n\n"
        f"Critical rules:\n"
        f"- pipeline: include ALL known developers, aim for completeness over caution\n"
        f"- {_CALIBRATION_RULES}\n"
        f"- est_launch must reflect local market launch, not reference country\n"
        f"- Return ONLY the JSON object. No preamble, no markdown fences, no explanation."
    )
