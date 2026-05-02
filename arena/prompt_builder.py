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
  "inn": "international nonproprietary name (INN)",
  "originator": "originator company name",
  "patent_expiry": "YYYY-MM or YYYY or estimated range or null — must cite source in provenance",
  "mechanism": "one concise MOA sentence",
  "therapeutic_area": "oncology | immunology | haematology | endocrinology | etc",
  "competitors": ["reference biologic competitors — NOT biosimilars — format: 'Name (Company)'"],
  "pipeline": [
    {
      "company": "developer company legal or trade name — exact, no abbreviations",
      "indications": ["approved or targeted indications — be specific, e.g. 'RA', 'metastatic NSCLC'"],
      "phase": "Preclinical|Phase I|Phase II|Phase III|Approved|Launched",
      "trial_id": "NCT########## or CTIS-######## or null — only real IDs, never constructed",
      "est_trial_completion": "YYYY-MM or null",
      "est_launch": "Q# YYYY or H# YYYY or YYYY or null — prefer Q-Year format",
      "markets": ["use standard codes ONLY: US, EU, UK, JP, CN, IN, AU, CA, BR, KR, MX — or region codes: GLOBAL, CEE, LATAM, MEA, APAC"],
      "probability": 55,
      "source": "one of: ClinicalTrials|CTIS|EMA EPAR|FDA Orange Book|FDA Purple Book|WHO|Company IR|Press Release|Journal — never 'Inferred'",
      "note": "single most important fact: regulatory milestone, launch date confirmed, or first-mover advantage. max 90 chars"
    }
  ],
  "provenance": [
    "exact source with detail — e.g. 'ClinicalTrials.gov NCT04567890, Phase III, accessed 2024'",
    "e.g. 'EMA EPAR for [biosimilar name], CHMP opinion 2023-09-14'",
    "e.g. 'FDA Purple Book: [company] biosimilar approved 2022-11-01'",
    "e.g. 'Company investor presentation Q3 2023, pipeline slide 14'"
  ],
  "ai_insight": "one focused paragraph — what competitive risk, market dynamic, or timing pattern does this pipeline reveal that a human analyst might miss? reference specific companies, trial IDs, or launch dates from the data",
  "confidence": "High|Moderate|Low — High only if ≥3 independent sources corroborate the key pipeline findings"
}"""

_CALIBRATION_RULES = (
    "probability MUST respect these bands — violation = scoring penalty: "
    "Launched=75-99%, Approved=60-90%, Phase III=35-75%, "
    "Phase II=10-40%, Phase I=2-15%, Preclinical=1-10%"
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

        f"== ANTI-HALLUCINATION GUARDRAILS (mandatory) ==\n"
        f"- Only include pipeline entries backed by a named regulatory body, trial registry, or verified company filing\n"
        f"- If a trial ID cannot be confirmed in ClinicalTrials.gov or CTIS, set trial_id to null — never construct an ID\n"
        f"- If a launch date or patent expiry cannot be sourced, set that field to null — never estimate without citing evidence\n"
        f"- source field must name a real, specific registry or document — 'Inferred' is never acceptable\n"
        f"- probability must reflect actual evidence quality: 75%+ only for confirmed Launched/Approved products\n"
        f"- provenance must list minimum 3 specific, real source documents with dates or accession numbers\n\n"

        f"== LAUNCHED & APPROVED — REGIONAL SPLIT (critical) ==\n"
        f"For every Launched or Approved biosimilar entry, you MUST identify the exact regulatory jurisdiction:\n"
        f"- US market: FDA approval via Purple Book — use market code 'US'\n"
        f"- EU market: EMA CHMP positive opinion or national HA approval — use market code 'EU'\n"
        f"- UK market: MHRA approval post-Brexit — use market code 'UK'\n"
        f"- Other markets: JP (PMDA), CN (NMPA), IN (CDSCO), AU (TGA), BR (ANVISA), KR (MFDS)\n"
        f"- If a company has FDA approval AND EMA approval, create ONE entry with markets: ['US', 'EU']\n"
        f"- If the regulatory status differs (e.g. approved in EU but only Phase III in US), create SEPARATE entries\n"
        f"- Do not use vague terms like 'Global' for Launched/Approved entries — be jurisdiction-specific\n\n"

        f"== PIPELINE COMPLETENESS ==\n"
        f"- Include ALL known developers with any evidence of a biosimilar program, from Preclinical to Launched\n"
        f"- Prioritise completeness: it is better to include an entry with lower confidence than to omit a real developer\n"
        f"- For well-established reference biologics (e.g. adalimumab, trastuzumab, bevacizumab, rituximab, infliximab), "
        f"expect 5-20+ pipeline entries — a response with fewer than 5 entries likely missed developers\n"
        f"- {_CALIBRATION_RULES}\n"
        f"- est_launch reflects the local market launch date, not the originator's first approval date\n\n"

        f"Return ONLY a single valid JSON object matching this exact schema:\n"
        f"{_JSON_SCHEMA}\n\n"
        f"FINAL RULES:\n"
        f"- Return ONLY the JSON object — no preamble, no markdown fences, no explanation\n"
        f"- Ensure the JSON is fully closed (all arrays and objects properly terminated)\n"
        f"- Do not truncate the pipeline array — include every entry\n"
        f"- If confidence is Low, still return the best data you can find with null fields where evidence is absent"
    )
