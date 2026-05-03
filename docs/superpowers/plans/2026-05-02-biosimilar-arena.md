# Biosimilar AI Race Arena — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack platform where 2–5 LLMs compete in parallel to extract biosimilar drug pipeline intelligence, scored and ranked in real time, deployed at aiqbiq.com on Railway.

**Architecture:** FastAPI backend dispatches all selected models in parallel via OpenRouter (production) or Anthropic API with different system prompts (demo mode), normalizes and scores each response, and serves a React 18 frontend from compiled static files.

**Tech Stack:** Python 3.11, FastAPI 0.135.1, asyncpg, httpx, tenacity, rapidfuzz, React 18, Vite 5, PostgreSQL 15, Railway

---

## File Map

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies with pinned versions |
| `config.py` | Environment variable loader |
| `main.py` | FastAPI app entry: lifespan, router registration, static file serving |
| `.env.example` | Template for all required env vars |
| `Procfile` | Railway process definition |
| `arena/__init__.py` | Package marker |
| `arena/model_registry.py` | 5 model definitions: OpenRouter IDs, system prompts, metadata |
| `arena/prompt_builder.py` | Unified extraction prompt + region modifier injection |
| `arena/client.py` | Async dispatcher: OpenRouter (production) and Anthropic (demo) modes |
| `arena/normalizer.py` | INN fuzzy match, date → Q+Year, probability clamping |
| `arena/scorer.py` | Multi-factor scoring engine + winner declaration |
| `routes/__init__.py` | Package marker |
| `routes/race.py` | POST /api/race: auth, cache, budget, orchestration |
| `db/__init__.py` | Package marker |
| `db/schema_race.sql` | 4 tables: race_results, model_leaderboard, race_daily_budget, audit_log |
| `db/connection.py` | asyncpg connection pool singleton |
| `db/cache.py` | cache_get / cache_set (PostgreSQL-backed, 7-day TTL) |
| `db/audit.py` | log_audit_pg: writes every race action to audit_log |
| `db/budget.py` | check_and_record_spend: daily USD guard |
| `tests/test_prompt_builder.py` | Unit: prompt content, region modifiers |
| `tests/test_normalizer.py` | Unit: date conversion, probability clamping, INN matching |
| `tests/test_scorer.py` | Unit: score factors, calibration penalty, winner declaration |
| `tests/test_client.py` | Unit: mocked HTTP, both modes, result shape |
| `tests/test_db_modules.py` | Unit: mocked pool, cache miss/hit, budget allow/block |
| `tests/test_race_api.py` | Integration: full endpoint against running server |
| `frontend/package.json` | React 18 + Vite 5 deps |
| `frontend/vite.config.js` | Vite config with /api proxy to localhost:8000 |
| `frontend/index.html` | HTML entry point |
| `frontend/src/main.jsx` | React root mount |
| `frontend/src/App.jsx` | Root component, passes ACCESS_KEY to RacePanel |
| `frontend/src/index.css` | CSS custom properties (light + dark mode) |
| `frontend/src/components/Race/ModelSelector.jsx` | Toggle cards for 5 models, 2–5 enforced |
| `frontend/src/components/Race/RacePanel.jsx` | Main race UI: lanes, results, tabs, leaderboard |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.env.example`
- Create: `Procfile`
- Create: `arena/__init__.py`
- Create: `routes/__init__.py`
- Create: `db/__init__.py`

- [ ] **Step 1: Initialize git**

```bash
cd "/Users/fareedkhan/Dev/Biosim Arena Comp- V2"
git init
echo "__pycache__/" > .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
echo "frontend/node_modules/" >> .gitignore
echo "frontend/dist/" >> .gitignore
echo ".venv/" >> .gitignore
```

- [ ] **Step 2: Write `requirements.txt`**

```
fastapi==0.135.1
uvicorn[standard]>=0.30.0
httpx>=0.27.0
tenacity>=8.3.0
rapidfuzz>=3.9.0
asyncpg>=0.29.0
python-dotenv>=1.0.0
```

- [ ] **Step 3: Write `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

USE_OPENROUTER             = os.getenv("USE_OPENROUTER", "false").lower() == "true"
OPENROUTER_API_KEY         = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE            = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
OPENROUTER_REFERER         = os.getenv("OPENROUTER_REFERER", "https://aiqbiq.com")
OPENROUTER_TITLE           = os.getenv("OPENROUTER_TITLE", "AIQBIQ Biosimilar Arena")
ANTHROPIC_API_KEY          = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_DEMO_MODEL       = os.getenv("ANTHROPIC_DEMO_MODEL", "claude-sonnet-4-20250514")
ACCESS_KEY                 = os.getenv("ACCESS_KEY", "")
DATABASE_URL               = os.getenv("DATABASE_URL", "")
ARENA_COST_DAILY_LIMIT_USD = float(os.getenv("ARENA_COST_DAILY_LIMIT_USD", "20"))
ARENA_CACHE_TTL_HOURS      = int(os.getenv("ARENA_CACHE_TTL_HOURS", "168"))
```

- [ ] **Step 4: Write `.env.example`**

```bash
# Toggle between demo (Anthropic only) and production (OpenRouter)
USE_OPENROUTER=false

# Required in production (USE_OPENROUTER=true)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE=https://openrouter.ai/api/v1
OPENROUTER_REFERER=https://aiqbiq.com
OPENROUTER_TITLE=AIQBIQ Biosimilar Arena

# Required in demo mode (USE_OPENROUTER=false)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_DEMO_MODEL=claude-sonnet-4-20250514

# Required always
ACCESS_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional, defaults shown
ARENA_COST_DAILY_LIMIT_USD=20
ARENA_CACHE_TTL_HOURS=168
```

- [ ] **Step 5: Write `Procfile`**

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 6: Create package markers**

```bash
touch arena/__init__.py routes/__init__.py db/__init__.py tests/__init__.py
```

- [ ] **Step 7: Install Python dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config.py .env.example Procfile .gitignore arena/__init__.py routes/__init__.py db/__init__.py tests/__init__.py
git commit -m "chore: project scaffold, deps, config, package structure"
```

---

## Task 2: Database Schema + Connection

**Files:**
- Create: `db/schema_race.sql`
- Create: `db/connection.py`

- [ ] **Step 1: Write `db/schema_race.sql`**

```sql
-- Race results cache (7-day TTL via expires_at)
CREATE TABLE IF NOT EXISTS race_results (
    id              SERIAL PRIMARY KEY,
    cache_key       TEXT NOT NULL UNIQUE,
    brand           TEXT NOT NULL,
    region          TEXT,
    model_keys      TEXT[] NOT NULL,
    winner          TEXT,
    winner_score    INT,
    winner_data     JSONB,
    rankings        JSONB NOT NULL DEFAULT '[]',
    consensus       BOOLEAN DEFAULT FALSE,
    extraction_ts   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    elapsed_s       NUMERIC(6,2)
);

CREATE INDEX IF NOT EXISTS idx_race_brand  ON race_results (brand);
CREATE INDEX IF NOT EXISTS idx_race_winner ON race_results (winner);
CREATE INDEX IF NOT EXISTS idx_race_ts     ON race_results (extraction_ts DESC);

-- Historical model performance per race
CREATE TABLE IF NOT EXISTS model_leaderboard (
    id          SERIAL PRIMARY KEY,
    model_key   TEXT NOT NULL,
    or_id       TEXT NOT NULL,
    race_ts     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    brand       TEXT NOT NULL,
    score_total INT NOT NULL,
    score_bd    JSONB,
    won         BOOLEAN DEFAULT FALSE,
    elapsed_s   NUMERIC(6,2)
);

CREATE INDEX IF NOT EXISTS idx_lb_model ON model_leaderboard (model_key);
CREATE INDEX IF NOT EXISTS idx_lb_ts    ON model_leaderboard (race_ts DESC);

-- Daily budget tracker (one row per UTC date)
CREATE TABLE IF NOT EXISTS race_daily_budget (
    budget_date     DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    total_usd_spent NUMERIC(8,4) DEFAULT 0,
    call_count      INT DEFAULT 0,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log for all race actions
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    action      TEXT NOT NULL,
    input_data  JSONB,
    output_data JSONB,
    logged_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_ts     ON audit_log (logged_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log (action);
```

- [ ] **Step 2: Write `db/connection.py`**

```python
import asyncpg
from config import DATABASE_URL

_pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

- [ ] **Step 3: Verify schema SQL is valid (no DB required)**

```bash
python -c "
with open('db/schema_race.sql') as f:
    sql = f.read()
# Verify all 4 tables present
for table in ['race_results', 'model_leaderboard', 'race_daily_budget', 'audit_log']:
    assert table in sql, f'Missing table: {table}'
print('Schema SQL: all 4 tables present')
"
```

Expected: `Schema SQL: all 4 tables present`

- [ ] **Step 4: Apply schema (requires running PostgreSQL)**

```bash
psql $DATABASE_URL -f db/schema_race.sql
```

Expected: Each `CREATE TABLE` and `CREATE INDEX` completes without error.

- [ ] **Step 5: Commit**

```bash
git add db/schema_race.sql db/connection.py
git commit -m "feat: database schema (4 tables) and asyncpg connection pool"
```

---

## Task 3: Model Registry

**Files:**
- Create: `arena/model_registry.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_model_registry.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_model_registry.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write `arena/model_registry.py`**

```python
MODEL_REGISTRY = {

    "analyst": {
        "or_id":     "anthropic/claude-sonnet-4-5",
        "label":     "The Analyst",
        "alias":     "Claude Sonnet",
        "color":     "#3266ad",
        "specialty": "Registry-first · NCT/CTIS · Audit-ready",
        "cost_tier": "high",
        "system": (
            "You are a precision biosimilar intelligence analyst. "
            "Your absolute priority is registry-verified evidence. "
            "Hunt for NCT IDs, CTIS IDs, EMA biosimilar pipeline listings, "
            "FDA Purple Book entries, and WHO prequalification data. "
            "Every pipeline entry must cite a specific verifiable source. "
            "Cross-reference originator USPTO and EPO patent filings to "
            "estimate patent expiry with primary vs secondary patent breakdown. "
            "Note the biosimilar regulatory pathway used (EMA similar "
            "biological medicinal product pathway, FDA 351(k), or national pathway). "
            "You are conservative — never list a developer without evidence. "
            "Return ONLY valid JSON, no markdown, no preamble."
        ),
    },

    "hunter": {
        "or_id":     "openai/gpt-4o",
        "label":     "The Hunter",
        "alias":     "GPT-4o",
        "color":     "#0F6E56",
        "specialty": "Launch timing · First-mover · CDMO signals",
        "cost_tier": "high",
        "system": (
            "You are an aggressive biosimilar market intelligence hunter. "
            "Your mission: maximum developer discovery. Cast the widest possible net. "
            "Look for Phase I programs, CDMO partnerships, licensing deals, "
            "equity filings, and conference disclosures. "
            "Your strength is launch timing prediction: identify which developers "
            "have commercial infrastructure, tender market experience, distribution "
            "partnerships, and regulatory submission readiness. "
            "Prioritize Asian manufacturers (Celltrion, Samsung Bioepis) who may "
            "have launched in Korea or EU before other regions. "
            "Look for interchangeability designation pursuit as ambition signals. "
            "Return ONLY valid JSON, no markdown, no preamble."
        ),
    },

    "scanner": {
        "or_id":     "google/gemini-2.0-flash-001",
        "label":     "The Scanner",
        "alias":     "Gemini Flash",
        "color":     "#854F0B",
        "specialty": "Global breadth · Emerging markets · WHO",
        "cost_tier": "low",
        "system": (
            "You are a global biosimilar surveillance scanner. "
            "Your core advantage is geographic breadth. "
            "Map the complete landscape: CEE (EMA-dependent but national HA required), "
            "LATAM (ANVISA/ANMAT/INVIMA separate pathways, local packaging delays 6-18mo), "
            "MEA (GCC tender cycles Q1/Q3, WHO prequalification as positive signal), "
            "and APAC (PMDA Japan, TGA Australia, NMPA China separate tracks). "
            "Flag biosimilars launched in reference markets not yet in LR markets — "
            "these are the highest near-term risk signals. "
            "Note WHO-prequalified biosimilar manufacturers. "
            "Track indication-specific programs where developers target different indications. "
            "Return ONLY valid JSON, no markdown."
        ),
    },

    "strategist": {
        "or_id":     "mistralai/mistral-large",
        "label":     "The Strategist",
        "alias":     "Mistral Large",
        "color":     "#534AB7",
        "specialty": "Market access · Payer logic · Tender cycles",
        "cost_tier": "medium",
        "system": (
            "You are a biosimilar market access and commercial strategist. "
            "Your unique lens is payer and reimbursement dynamics. "
            "Beyond pipeline tracking, assess which developers have commercial "
            "positioning to win: formulary status in major markets, INN prescribing "
            "policies, mandatory substitution frameworks, government tender wins, "
            "pharmacist substitution uptake. "
            "Flag rebate strategies, risk-sharing agreements, and patient support "
            "programs driving market share. "
            "Assess developer commercial capabilities: own sales force vs distribution. "
            "Note financial sustainability of biosimilar programs. "
            "Return ONLY valid JSON, no markdown."
        ),
    },

    "challenger": {
        "or_id":     "meta-llama/llama-3.1-70b-instruct",
        "label":     "The Challenger",
        "alias":     "Llama 3.1 70B",
        "color":     "#993C1D",
        "specialty": "Unconstrained · Maximum scope · API manufacturing",
        "cost_tier": "low",
        "system": (
            "You are an unconstrained biosimilar intelligence challenger. "
            "Your mandate is maximum completeness without artificial conservatism. "
            "Cast the broadest possible net: every known developer, announced program, "
            "speculated entry, and plausible candidate based on manufacturing capability. "
            "Note when a company has CDMO capabilities to develop a biosimilar even "
            "if no program is publicly announced. "
            "Flag companies that filed patents on biosimilar production processes. "
            "Look at conference abstracts, posters, academic collaborations as "
            "early-stage signals. "
            "Note regulatory signals: IMPD submissions, clinical trial authorizations. "
            "Be aggressive with probability — better to flag a potential entrant "
            "than miss one. "
            "Return ONLY valid JSON, no markdown."
        ),
    },
}

OPENROUTER_MODELS = {m["or_id"] for m in MODEL_REGISTRY.values()}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_model_registry.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add arena/model_registry.py tests/test_model_registry.py
git commit -m "feat: model registry with 5 OpenRouter models and system prompts"
```

---

## Task 4: Prompt Builder

**Files:**
- Create: `arena/prompt_builder.py`
- Create: `tests/test_prompt_builder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_prompt_builder.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `arena/prompt_builder.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_prompt_builder.py -v
```

Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add arena/prompt_builder.py tests/test_prompt_builder.py
git commit -m "feat: prompt builder with region modifiers and calibration rules"
```

---

## Task 5: Normalizer

**Files:**
- Create: `arena/normalizer.py`
- Create: `tests/test_normalizer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_normalizer.py
import pytest
from arena.normalizer import normalize_inn, normalize_date, clamp_probability, normalize_outputs


def test_normalize_date_january():
    assert normalize_date("2026-01") == "Q1 2026"


def test_normalize_date_april():
    assert normalize_date("2026-04") == "Q2 2026"


def test_normalize_date_july():
    assert normalize_date("2026-07") == "Q3 2026"


def test_normalize_date_october():
    assert normalize_date("2026-10") == "Q4 2026"


def test_normalize_date_already_qyear():
    assert normalize_date("Q2 2026") == "Q2 2026"


def test_normalize_date_year_only():
    assert normalize_date("2026") == "2026"


def test_normalize_date_none():
    assert normalize_date(None) is None


def test_clamp_phase_iii_above():
    assert clamp_probability(100, "Phase III") == 90


def test_clamp_phase_iii_below():
    assert clamp_probability(10, "Phase III") == 35


def test_clamp_phase_iii_in_band():
    assert clamp_probability(65, "Phase III") == 65


def test_clamp_phase_ii_above():
    assert clamp_probability(50, "Phase II") == 40


def test_clamp_phase_ii_below():
    assert clamp_probability(5, "Phase II") == 10


def test_clamp_unknown_phase():
    assert clamp_probability(75, "Unknown") == 75


def test_normalize_inn_exact():
    assert normalize_inn("nivolumab") == "nivolumab"


def test_normalize_inn_near_match():
    result = normalize_inn("nivolumabb")
    assert result == "nivolumab"


def test_normalize_inn_empty():
    assert normalize_inn("") == ""


def test_normalize_outputs_date_conversion():
    raw = [{
        "model_key": "analyst",
        "output": {
            "inn": "nivolumab",
            "pipeline": [{"est_launch": "2026-04", "probability": 100, "phase": "Phase III", "note": ""}],
        },
        "error": None,
        "elapsed": 2.1,
    }]
    result = normalize_outputs(raw)
    assert result[0]["output"]["pipeline"][0]["est_launch"] == "Q2 2026"


def test_normalize_outputs_probability_clamping():
    raw = [{
        "model_key": "analyst",
        "output": {
            "inn": "nivolumab",
            "pipeline": [{"est_launch": None, "probability": 100, "phase": "Phase III", "note": ""}],
        },
        "error": None,
        "elapsed": 2.1,
    }]
    result = normalize_outputs(raw)
    assert result[0]["output"]["pipeline"][0]["probability"] == 90


def test_normalize_outputs_passes_through_elapsed():
    raw = [{"model_key": "analyst", "output": None, "error": "timeout", "elapsed": 45.0}]
    result = normalize_outputs(raw)
    assert result[0]["elapsed"] == 45.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_normalizer.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `arena/normalizer.py`**

```python
import re
from rapidfuzz import fuzz

KNOWN_INNS = [
    "adalimumab", "bevacizumab", "rituximab", "trastuzumab", "etanercept",
    "infliximab", "nivolumab", "pembrolizumab", "atezolizumab", "durvalumab",
    "cetuximab", "panitumumab", "ranibizumab", "aflibercept", "ustekinumab",
    "secukinumab", "ixekizumab", "guselkumab", "risankizumab", "denosumab",
    "tocilizumab", "sarilumab", "abatacept", "natalizumab", "ocrelizumab",
    "eculizumab", "ravulizumab", "omalizumab", "mepolizumab", "benralizumab",
    "dupilumab", "tezepelumab", "brodalumab", "bimekizumab",
]

MONTH_TO_QUARTER = {
    "01": "Q1", "02": "Q1", "03": "Q1",
    "04": "Q2", "05": "Q2", "06": "Q2",
    "07": "Q3", "08": "Q3", "09": "Q3",
    "10": "Q4", "11": "Q4", "12": "Q4",
}

PHASE_BANDS = {
    "phase iii":  (35, 90),
    "phase ii":   (10, 40),
    "phase i":    (0,  10),
    "preclinical":(0,  10),
    "approved":   (55, 85),
    "launched":   (40, 80),
}


def normalize_inn(inn: str) -> str:
    if not inn:
        return inn
    inn_lower = inn.lower().strip()
    best = max(KNOWN_INNS, key=lambda x: fuzz.ratio(inn_lower, x), default=inn_lower)
    return best if fuzz.ratio(inn_lower, best) >= 80 else inn_lower


def normalize_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    if re.match(r"^[QH][1-4]\s*\d{4}$", date_str):
        return date_str
    m = re.match(r"^(\d{4})-(\d{2})$", date_str)
    if m:
        year, month = m.group(1), m.group(2)
        quarter = MONTH_TO_QUARTER.get(month)
        return f"{quarter} {year}" if quarter else year
    if re.match(r"^\d{4}$", date_str):
        return date_str
    return date_str


def clamp_probability(probability, phase: str) -> int:
    try:
        prob = int(probability)
    except (TypeError, ValueError):
        return 50
    phase_lower = (phase or "").lower()
    for key, (lo, hi) in PHASE_BANDS.items():
        if key in phase_lower:
            return max(lo, min(hi, prob))
    return max(0, min(100, prob))


def _normalize_one(result: dict) -> dict:
    output = result.get("output")
    if not output:
        return result
    normalized = dict(output)
    if normalized.get("inn"):
        normalized["inn"] = normalize_inn(normalized["inn"])
    norm_pipe = []
    for entry in normalized.get("pipeline", []):
        entry = dict(entry)
        if entry.get("est_launch"):
            entry["est_launch"] = normalize_date(entry["est_launch"])
        if entry.get("probability") is not None and entry.get("phase"):
            entry["probability"] = clamp_probability(entry["probability"], entry["phase"])
        norm_pipe.append(entry)
    normalized["pipeline"] = norm_pipe
    return {**result, "output": normalized}


def normalize_outputs(results: list[dict]) -> list[dict]:
    return [_normalize_one(r) for r in results]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_normalizer.py -v
```

Expected: 19 tests PASS

- [ ] **Step 5: Commit**

```bash
git add arena/normalizer.py tests/test_normalizer.py
git commit -m "feat: normalizer — INN fuzzy match, Q+Year dates, probability clamping"
```

---

## Task 6: Scoring Engine

**Files:**
- Create: `arena/scorer.py`
- Create: `tests/test_scorer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scorer.py
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
        {"model_key": "analyst",  "output": SAMPLE, "elapsed": 2.1, "error": None},
        {"model_key": "scanner",  "output": SAMPLE, "elapsed": 3.0, "error": None},
    ]
    outcome = score_and_declare_winner(results)
    assert outcome["consensus"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scorer.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `arena/scorer.py`**

```python
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
        return {"total": 0, "bd": {k: 0 for k in SCORE_CONFIG}, "penalized": 0}

    c    = SCORE_CONFIG
    pipe = data.get("pipeline", [])
    bd   = {}

    bd["developers"] = min(len(pipe) * c["developer_pts"], c["developer_max"])
    bd["provenance"] = min(len(data.get("provenance", [])) * c["provenance_pts"], c["provenance_max"])

    q_yr = sum(
        1 for p in pipe
        if p.get("est_launch") and re.match(r"^[QH][1-4]\s*\d{4}", p["est_launch"] or "")
    )
    bd["launches"]   = min(q_yr * c["launch_q_pts"], c["launch_max"])

    has_id = sum(
        1 for p in pipe
        if p.get("trial_id") and p["trial_id"] not in (None, "null", "")
    )
    bd["trial_ids"]  = min(has_id * c["trial_id_pts"], c["trial_id_max"])
    bd["patent"]     = c["patent_pts"] if (data.get("patent_expiry") and data["patent_expiry"] not in (None, "null", "")) else 0
    bd["competitors"]= min(len(data.get("competitors", [])) * c["competitor_pts"], c["competitor_max"])
    bd["insight"]    = c["insight_pts"] if len(data.get("ai_insight", "")) > 60 else 0
    bd["speed"]      = 0

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scorer.py -v
```

Expected: 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add arena/scorer.py tests/test_scorer.py
git commit -m "feat: scoring engine — multi-factor points, calibration penalty, winner declaration"
```

---

## Task 7: OpenRouter + Anthropic Client

**Files:**
- Create: `arena/client.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_client.py
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openrouter_response(payload: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 500},
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_anthropic_response(payload: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"text": json.dumps(payload)}],
        "usage": {"input_tokens": 100, "output_tokens": 500},
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.mark.asyncio
async def test_run_race_returns_all_model_keys():
    payload = {"pipeline": [], "provenance": []}
    mock_resp = _make_openrouter_response(payload)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("arena.client.USE_OPENROUTER", True), \
         patch("httpx.AsyncClient", return_value=mock_cm):
        import importlib, arena.client
        importlib.reload(arena.client)
        from arena.client import run_race
        results = await run_race("test prompt", ["analyst", "scanner"])

    assert len(results) == 2
    keys = {r["model_key"] for r in results}
    assert keys == {"analyst", "scanner"}


@pytest.mark.asyncio
async def test_run_race_includes_elapsed():
    payload = {"pipeline": [], "provenance": []}
    mock_resp = _make_openrouter_response(payload)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("arena.client.USE_OPENROUTER", True), \
         patch("httpx.AsyncClient", return_value=mock_cm):
        import importlib, arena.client
        importlib.reload(arena.client)
        from arena.client import run_race
        results = await run_race("test prompt", ["analyst"])

    assert "elapsed" in results[0]
    assert isinstance(results[0]["elapsed"], float)


@pytest.mark.asyncio
async def test_run_race_handles_json_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "not valid json {{"}}],
        "usage": {},
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("arena.client.USE_OPENROUTER", True), \
         patch("arena.client._call_openrouter.__wrapped__", side_effect=None), \
         patch("httpx.AsyncClient", return_value=mock_cm):
        import importlib, arena.client
        importlib.reload(arena.client)
        from arena.client import run_race
        results = await run_race("test prompt", ["analyst"])

    assert results[0]["output"] is None or results[0].get("error") is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_client.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `arena/client.py`**

```python
import asyncio
import json
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .model_registry import MODEL_REGISTRY
from config import (
    USE_OPENROUTER,
    OPENROUTER_BASE, OPENROUTER_API_KEY, OPENROUTER_REFERER, OPENROUTER_TITLE,
    ANTHROPIC_API_KEY, ANTHROPIC_DEMO_MODEL,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
)
async def _call_openrouter(model_key: str, prompt: str, client: httpx.AsyncClient) -> dict:
    meta = MODEL_REGISTRY[model_key]
    t0   = time.time()
    try:
        r = await client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer":  OPENROUTER_REFERER,
                "X-Title":       OPENROUTER_TITLE,
                "Content-Type":  "application/json",
            },
            json={
                "model":    meta["or_id"],
                "messages": [
                    {"role": "system", "content": meta["system"]},
                    {"role": "user",   "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens":  2000,
            },
            timeout=45.0,
        )
        r.raise_for_status()
        data  = r.json()
        raw   = data["choices"][0]["message"]["content"]
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return {
            "model_key": model_key, "or_id": meta["or_id"],
            "output": json.loads(clean), "usage": data.get("usage", {}),
            "error": None, "elapsed": round(time.time() - t0, 2),
        }
    except json.JSONDecodeError as e:
        return {"model_key": model_key, "or_id": meta["or_id"], "output": None, "usage": {},
                "error": f"JSON: {e}", "elapsed": round(time.time() - t0, 2)}
    except httpx.HTTPStatusError as e:
        return {"model_key": model_key, "or_id": meta["or_id"], "output": None, "usage": {},
                "error": f"HTTP {e.response.status_code}", "elapsed": round(time.time() - t0, 2)}
    except Exception as e:
        return {"model_key": model_key, "or_id": meta["or_id"], "output": None, "usage": {},
                "error": str(e), "elapsed": round(time.time() - t0, 2)}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
)
async def _call_anthropic_demo(model_key: str, prompt: str, client: httpx.AsyncClient) -> dict:
    meta = MODEL_REGISTRY[model_key]
    t0   = time.time()
    try:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type":      "application/json",
            },
            json={
                "model":      ANTHROPIC_DEMO_MODEL,
                "max_tokens": 2000,
                "system":     meta["system"],
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=45.0,
        )
        r.raise_for_status()
        data  = r.json()
        raw   = (data.get("content") or [{}])[0].get("text", "{}")
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return {
            "model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL,
            "output": json.loads(clean), "usage": data.get("usage", {}),
            "error": None, "elapsed": round(time.time() - t0, 2),
        }
    except json.JSONDecodeError as e:
        return {"model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL, "output": None, "usage": {},
                "error": f"JSON: {e}", "elapsed": round(time.time() - t0, 2)}
    except httpx.HTTPStatusError as e:
        return {"model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL, "output": None, "usage": {},
                "error": f"HTTP {e.response.status_code}", "elapsed": round(time.time() - t0, 2)}
    except Exception as e:
        return {"model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL, "output": None, "usage": {},
                "error": str(e), "elapsed": round(time.time() - t0, 2)}


async def run_race(prompt: str, model_keys: list[str]) -> list[dict]:
    call_fn = _call_openrouter if USE_OPENROUTER else _call_anthropic_demo
    async with httpx.AsyncClient() as client:
        tasks   = [call_fn(k, prompt, client) for k in model_keys]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_client.py -v
```

Expected: Tests PASS (the JSON error test may produce error in output or None — either is acceptable)

- [ ] **Step 5: Commit**

```bash
git add arena/client.py tests/test_client.py
git commit -m "feat: async OpenRouter + Anthropic demo client, retries, both response formats"
```

---

## Task 8: DB Modules

**Files:**
- Create: `db/cache.py`
- Create: `db/audit.py`
- Create: `db/budget.py`
- Create: `tests/test_db_modules.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_db_modules.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date


def _mock_pool(fetchrow_return=None, execute_return=None):
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    mock_conn.execute  = AsyncMock(return_value=execute_return)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__  = AsyncMock(return_value=False)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_cm)
    return mock_pool, mock_conn


@pytest.mark.asyncio
async def test_cache_get_miss():
    pool, _ = _mock_pool(fetchrow_return=None)
    with patch("db.cache.get_pool", AsyncMock(return_value=pool)):
        from db import cache
        import importlib; importlib.reload(cache)
        result = await cache.cache_get("missing_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_calls_execute():
    pool, conn = _mock_pool()
    with patch("db.cache.get_pool", AsyncMock(return_value=pool)):
        from db import cache
        import importlib; importlib.reload(cache)
        await cache.cache_set("k1", {"brand": "Opdivo", "winner": "analyst",
                                      "winner_score": 80, "winner_data": {},
                                      "rankings": [], "consensus": False,
                                      "model_keys": ["analyst"], "region": "",
                                      "elapsed_s": 2.1})
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_budget_allows_under_limit():
    pool, _ = _mock_pool(fetchrow_return={"total_usd_spent": 5.0})
    with patch("db.budget.get_pool", AsyncMock(return_value=pool)), \
         patch("db.budget.DAILY_LIMIT", 20.0):
        from db import budget
        import importlib; importlib.reload(budget)
        result = await budget.check_and_record_spend("race", estimated_usd=0.05)
    assert result is True


@pytest.mark.asyncio
async def test_budget_blocks_over_limit():
    pool, _ = _mock_pool(fetchrow_return={"total_usd_spent": 19.99})
    with patch("db.budget.get_pool", AsyncMock(return_value=pool)), \
         patch("db.budget.DAILY_LIMIT", 20.0):
        from db import budget
        import importlib; importlib.reload(budget)
        result = await budget.check_and_record_spend("race", estimated_usd=0.05)
    assert result is False


@pytest.mark.asyncio
async def test_budget_allows_no_spend_today():
    pool, _ = _mock_pool(fetchrow_return=None)
    with patch("db.budget.get_pool", AsyncMock(return_value=pool)), \
         patch("db.budget.DAILY_LIMIT", 20.0):
        from db import budget
        import importlib; importlib.reload(budget)
        result = await budget.check_and_record_spend("race", estimated_usd=0.05)
    assert result is True


@pytest.mark.asyncio
async def test_audit_calls_execute():
    pool, conn = _mock_pool()
    with patch("db.audit.get_pool", AsyncMock(return_value=pool)):
        from db import audit
        import importlib; importlib.reload(audit)
        await audit.log_audit_pg("race", {"brand": "Opdivo"}, {"winner": "analyst"})
    conn.execute.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db_modules.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `db/cache.py`**

```python
import json
from datetime import datetime, timedelta
from db.connection import get_pool


async def cache_get(key: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT winner, winner_score, winner_data, rankings, consensus,
                   extraction_ts, elapsed_s, brand, region, model_keys
            FROM race_results
            WHERE cache_key = $1
              AND (expires_at IS NULL OR expires_at > NOW())
            """,
            key,
        )
    if not row:
        return None
    return {
        "winner":        row["winner"],
        "winner_score":  row["winner_score"],
        "winner_data":   row["winner_data"],
        "rankings":      row["rankings"],
        "consensus":     row["consensus"],
        "extraction_ts": row["extraction_ts"].isoformat() if row["extraction_ts"] else None,
        "elapsed_s":     float(row["elapsed_s"]) if row["elapsed_s"] else None,
        "brand":         row["brand"],
        "region":        row["region"],
        "model_keys":    list(row["model_keys"]),
    }


async def cache_set(key: str, result: dict, ttl_hours: int = 168) -> None:
    pool    = await get_pool()
    expires = datetime.utcnow() + timedelta(hours=ttl_hours)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO race_results
                (cache_key, brand, region, model_keys, winner, winner_score,
                 winner_data, rankings, consensus, extraction_ts, expires_at, elapsed_s)
            VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9,$10,$11,$12)
            ON CONFLICT (cache_key) DO UPDATE SET
                winner        = EXCLUDED.winner,
                winner_score  = EXCLUDED.winner_score,
                winner_data   = EXCLUDED.winner_data,
                rankings      = EXCLUDED.rankings,
                consensus     = EXCLUDED.consensus,
                extraction_ts = EXCLUDED.extraction_ts,
                expires_at    = EXCLUDED.expires_at,
                elapsed_s     = EXCLUDED.elapsed_s
            """,
            key,
            result.get("brand", ""),
            result.get("region", ""),
            result.get("model_keys", []),
            result.get("winner"),
            result.get("winner_score"),
            json.dumps(result.get("winner_data")),
            json.dumps(result.get("rankings", [])),
            result.get("consensus", False),
            datetime.utcnow(),
            expires,
            result.get("elapsed_s"),
        )
```

- [ ] **Step 4: Write `db/audit.py`**

```python
import json
from datetime import datetime
from db.connection import get_pool


async def log_audit_pg(action: str, input_data: dict, output_data: dict) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log (action, input_data, output_data, logged_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4)
            """,
            action,
            json.dumps(input_data),
            json.dumps(output_data),
            datetime.utcnow(),
        )
```

- [ ] **Step 5: Write `db/budget.py`**

```python
import os
from datetime import date
from db.connection import get_pool

DAILY_LIMIT = float(os.getenv("ARENA_COST_DAILY_LIMIT_USD", "20"))


async def check_and_record_spend(action: str, estimated_usd: float) -> bool:
    pool  = await get_pool()
    today = date.today()
    async with pool.acquire() as conn:
        row     = await conn.fetchrow(
            "SELECT total_usd_spent FROM race_daily_budget WHERE budget_date = $1",
            today,
        )
        current = float(row["total_usd_spent"]) if row else 0.0
        if current + estimated_usd > DAILY_LIMIT:
            return False
        await conn.execute(
            """
            INSERT INTO race_daily_budget (budget_date, total_usd_spent, call_count, last_updated)
            VALUES ($1, $2, 1, NOW())
            ON CONFLICT (budget_date) DO UPDATE SET
                total_usd_spent = race_daily_budget.total_usd_spent + EXCLUDED.total_usd_spent,
                call_count      = race_daily_budget.call_count + 1,
                last_updated    = NOW()
            """,
            today,
            estimated_usd,
        )
    return True
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_db_modules.py -v
```

Expected: 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add db/cache.py db/audit.py db/budget.py tests/test_db_modules.py
git commit -m "feat: DB modules — PostgreSQL-backed cache, audit log, daily budget guard"
```

---

## Task 9: Race Endpoint + main.py

**Files:**
- Create: `routes/race.py`
- Create: `main.py`

- [ ] **Step 1: Write `routes/race.py`**

```python
import os
import time
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from arena.client          import run_race
from arena.prompt_builder  import build_race_prompt
from arena.scorer          import score_and_declare_winner
from arena.normalizer      import normalize_outputs
from arena.model_registry  import MODEL_REGISTRY
from db.cache              import cache_get, cache_set
from db.audit              import log_audit_pg
from db.budget             import check_and_record_spend

router     = APIRouter()
ACCESS_KEY = os.getenv("ACCESS_KEY", "")


class RaceRequest(BaseModel):
    brand:      str
    model_keys: list[str]
    region:     Optional[str] = ""
    molecule:   Optional[str] = ""


@router.post("/api/race")
async def race_endpoint(req: RaceRequest, x_access_key: str = Header(default="")):

    if x_access_key != ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    invalid = [k for k in req.model_keys if k not in MODEL_REGISTRY]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown model keys: {invalid}")
    if not (2 <= len(req.model_keys) <= 5):
        raise HTTPException(status_code=400, detail="Select between 2 and 5 models")

    cache_key = f"race:{req.brand.lower()}:{':'.join(sorted(req.model_keys))}:{req.region}"
    cached    = await cache_get(cache_key)
    if cached:
        return {**cached, "source": "cache"}

    est_cost = len(req.model_keys) * 0.04
    if not await check_and_record_spend("race", estimated_usd=est_cost):
        raise HTTPException(status_code=429, detail="Daily race budget exceeded. Resets UTC midnight.")

    prompt  = build_race_prompt(brand=req.brand, region=req.region or "", molecule=req.molecule or "")
    t_start = time.time()
    raw     = await run_race(prompt, req.model_keys)
    elapsed = round(time.time() - t_start, 2)

    normalized = normalize_outputs(raw)
    result     = score_and_declare_winner(normalized)

    result["brand"]      = req.brand
    result["region"]     = req.region
    result["model_keys"] = req.model_keys
    result["elapsed_s"]  = elapsed

    await cache_set(cache_key, result, ttl_hours=168)
    await log_audit_pg(
        action="race",
        input_data=req.model_dump(),
        output_data={
            "winner":       result.get("winner"),
            "winner_score": result.get("winner_score"),
            "models_run":   len(req.model_keys),
            "elapsed_s":    elapsed,
        },
    )

    return {**result, "source": "live"}
```

- [ ] **Step 2: Write `main.py`**

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes.race       import router as race_router
from db.connection     import get_pool, close_pool
from arena.model_registry import MODEL_REGISTRY


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="Biosimilar AI Race Arena", lifespan=lifespan)
app.include_router(race_router)


@app.get("/api/health")
async def health():
    return {
        "status":            "ok",
        "db_type":           "postgresql",
        "race_arena":        "enabled",
        "models_available":  list(MODEL_REGISTRY.keys()),
        "openrouter":        bool(os.getenv("OPENROUTER_API_KEY")),
    }


_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    _assets = os.path.join(_frontend_dist, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
```

- [ ] **Step 3: Verify the app imports without error (no DB needed)**

```bash
python -c "
import os; os.environ['DATABASE_URL'] = 'postgresql://x'
from main import app
print('main.py imports OK')
print('Routes:', [r.path for r in app.routes])
"
```

Expected: `main.py imports OK` followed by routes list including `/api/race` and `/api/health`

- [ ] **Step 4: Write integration tests**

```python
# tests/test_race_api.py
import pytest
import httpx

BASE = "http://localhost:8000"
KEY  = "test-key"


@pytest.mark.asyncio
async def test_race_auth_required():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            json={"brand": "Opdivo", "model_keys": ["analyst", "hunter"], "region": ""},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_race_model_validation():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Keytruda", "model_keys": ["unknown_model"], "region": ""},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_race_min_models():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Opdivo", "model_keys": ["analyst"], "region": ""},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_race_max_models():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Opdivo", "model_keys": ["analyst","hunter","scanner","strategist","challenger","analyst"], "region": ""},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "analyst" in data["models_available"]


@pytest.mark.asyncio
async def test_race_returns_winner():
    """Requires running server with valid API key and real model access."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Opdivo", "model_keys": ["analyst", "scanner"], "region": "CEE"},
            timeout=90.0,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "winner" in data
    assert data["winner"] in ["analyst", "scanner"]
    assert len(data["rankings"]) == 2
    assert data["source"] in ("live", "cache")


@pytest.mark.asyncio
async def test_race_caches():
    payload = {"brand": "TestBrandXYZ", "model_keys": ["analyst", "hunter"], "region": "MEA"}
    async with httpx.AsyncClient() as client:
        r1 = await client.post(f"{BASE}/api/race", headers={"x-access-key": KEY}, json=payload, timeout=90.0)
        r2 = await client.post(f"{BASE}/api/race", headers={"x-access-key": KEY}, json=payload, timeout=10.0)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["source"] == "cache"
```

- [ ] **Step 5: Run auth/validation unit-style integration tests (no network)**

Start the server in demo mode first (requires ANTHROPIC_API_KEY or just test auth/validation):

```bash
ACCESS_KEY=test-key DATABASE_URL=postgresql://x uvicorn main:app --port 8000 &
sleep 2
pytest tests/test_race_api.py::test_race_auth_required tests/test_race_api.py::test_race_model_validation tests/test_race_api.py::test_race_min_models tests/test_race_api.py::test_race_max_models tests/test_race_api.py::test_health_endpoint -v --asyncio-mode=auto
```

Expected: 5 tests PASS (these don't call LLMs)

- [ ] **Step 6: Kill background server**

```bash
pkill -f "uvicorn main:app"
```

- [ ] **Step 7: Commit**

```bash
git add routes/race.py main.py tests/test_race_api.py
git commit -m "feat: POST /api/race endpoint, GET /api/health, FastAPI app entry"
```

---

## Task 10: Frontend Scaffold + ModelSelector

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/components/Race/ModelSelector.jsx`

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "biosimilar-arena-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "chart.js": "^4.4.0",
    "jspdf": "^2.5.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: Write `frontend/vite.config.js`**

```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
```

- [ ] **Step 3: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Biosimilar AI Race Arena — AIQBIQ</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Write `frontend/src/main.jsx`**

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 5: Write `frontend/src/components/Race/ModelSelector.jsx`**

```jsx
const MODELS = [
  { id: "analyst",    label: "The Analyst",    alias: "Claude Sonnet",  color: "#3266ad", specialty: "Registry-first · NCT/CTIS · Audit-ready" },
  { id: "hunter",     label: "The Hunter",     alias: "GPT-4o",         color: "#0F6E56", specialty: "Launch timing · First-mover · CDMO signals" },
  { id: "scanner",    label: "The Scanner",    alias: "Gemini Flash",   color: "#854F0B", specialty: "Global breadth · Emerging markets · WHO" },
  { id: "strategist", label: "The Strategist", alias: "Mistral Large",  color: "#534AB7", specialty: "Market access · Payer logic · Tender cycles" },
  { id: "challenger", label: "The Challenger", alias: "Llama 3.1 70B", color: "#993C1D", specialty: "Unconstrained · Max scope · Manufacturing signals" },
];

export default function ModelSelector({ selected, onToggle }) {
  return (
    <div>
      <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.07em",
                  color: "var(--color-text-secondary)", marginBottom: 10 }}>
        Select racers — min 2, max 5
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 8 }}>
        {MODELS.map((m) => {
          const on = selected.includes(m.id);
          return (
            <div
              key={m.id}
              onClick={() => onToggle(m.id)}
              style={{
                cursor: "pointer", userSelect: "none",
                border: on ? `2px solid ${m.color}` : "0.5px solid var(--color-border-tertiary)",
                borderRadius: "var(--border-radius-lg)",
                padding: "0.75rem",
                background: on ? "var(--color-background-secondary)" : "var(--color-background-primary)",
              }}
            >
              <p style={{ fontSize: 10, color: "var(--color-text-secondary)", textTransform: "uppercase",
                          letterSpacing: "0.05em", margin: "0 0 2px" }}>{m.label}</p>
              <p style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 3px" }}>{m.alias}</p>
              <p style={{ fontSize: 11, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.4 }}>{m.specialty}</p>
              {on && <p style={{ fontSize: 11, color: m.color, margin: "6px 0 0", fontWeight: 500 }}>✓ Selected</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Install frontend dependencies**

```bash
cd frontend && npm install
```

Expected: `node_modules/` created, no errors

- [ ] **Step 7: Verify Vite builds without component errors**

```bash
cd frontend && npm run build
```

Expected: Build succeeds (will fail until App.jsx exists — do this after Task 12)

- [ ] **Step 8: Commit**

```bash
cd ..
git add frontend/package.json frontend/vite.config.js frontend/index.html frontend/src/main.jsx frontend/src/components/Race/ModelSelector.jsx
git commit -m "feat: frontend scaffold (Vite + React 18) and ModelSelector component"
```

---

## Task 11: RacePanel Component

**Files:**
- Create: `frontend/src/components/Race/RacePanel.jsx`

- [ ] **Step 1: Write `frontend/src/components/Race/RacePanel.jsx`**

```jsx
import { useState } from "react";
import { jsPDF } from "jspdf";
import ModelSelector from "./ModelSelector";

const MODEL_META = {
  analyst:    { label: "The Analyst",    alias: "Claude Sonnet",  color: "#3266ad" },
  hunter:     { label: "The Hunter",     alias: "GPT-4o",         color: "#0F6E56" },
  scanner:    { label: "The Scanner",    alias: "Gemini Flash",   color: "#854F0B" },
  strategist: { label: "The Strategist", alias: "Mistral Large",  color: "#534AB7" },
  challenger: { label: "The Challenger", alias: "Llama 3.1 70B", color: "#993C1D" },
};

function formatBrief(d) {
  if (!d) return "No data extracted.";
  const pipe = d.pipeline || [];
  const sep  = "─".repeat(48);
  let t = "";
  t += `BRAND          ${d.brand || "—"}\n`;
  t += `INN            ${d.inn || "—"}\n`;
  t += `ORIGINATOR     ${d.originator || "—"}\n`;
  t += `MECHANISM      ${d.mechanism || "—"}\n`;
  t += `PATENT EXPIRY  ${d.patent_expiry || "Not identified"}\n`;
  t += `AREA           ${d.therapeutic_area || "—"}\n`;
  t += `CONFIDENCE     ${d.confidence || "—"}\n\n`;
  if ((d.competitors || []).length) {
    t += `REFERENCE COMPETITORS\n`;
    d.competitors.forEach((c) => { t += `  · ${c}\n`; });
    t += "\n";
  }
  t += `BIOSIMILAR PIPELINE — ${pipe.length} developer(s) identified\n${sep}\n`;
  pipe.forEach((p) => {
    t += `\n${p.company || "Unknown"}\n`;
    t += `  Indications   ${(p.indications || []).join(", ") || "—"}\n`;
    t += `  Phase         ${p.phase || "—"}\n`;
    if (p.trial_id && p.trial_id !== "null") t += `  Trial ID      ${p.trial_id}\n`;
    if (p.est_trial_completion) t += `  Trial end     ${p.est_trial_completion}\n`;
    const mkt = (p.markets || []).join(", ") || "—";
    if (p.est_launch) t += `  Est. launch   ${p.est_launch}  |  Markets: ${mkt}\n`;
    else              t += `  Markets       ${mkt}\n`;
    t += `  Probability   ${p.probability}%  [${p.source || "—"}]\n`;
    if (p.note) t += `  Note          ${p.note}\n`;
  });
  t += `\n${sep}\nPROVENANCE\n`;
  (d.provenance || []).forEach((s) => { t += `  · ${s}\n`; });
  return t;
}

function exportPDF(brand, winnerAlias, briefText, aiInsight) {
  const doc = new jsPDF();
  doc.setFontSize(14);
  doc.text(`Biosimilar Intelligence Brief: ${brand}`, 14, 20);
  doc.setFontSize(10);
  doc.text(`Winner: ${winnerAlias}`, 14, 30);
  doc.setFontSize(8);
  const lines = doc.splitTextToSize(briefText, 180);
  doc.text(lines, 14, 42);
  if (aiInsight) {
    const y = 42 + lines.length * 4 + 8;
    doc.setFontSize(9);
    doc.text("AI Insight:", 14, y);
    doc.setFontSize(8);
    const ilines = doc.splitTextToSize(aiInsight, 180);
    doc.text(ilines, 14, y + 6);
  }
  doc.save(`biosimilar-brief-${brand.toLowerCase().replace(/\s+/g, "-")}.pdf`);
}

export default function RacePanel({ accessKey }) {
  const [brand,    setBrand]    = useState("");
  const [region,   setRegion]   = useState("");
  const [selected, setSelected] = useState(["analyst", "hunter", "scanner"]);
  const [racing,   setRacing]   = useState(false);
  const [result,   setResult]   = useState(null);
  const [error,    setError]    = useState(null);
  const [tab,      setTab]      = useState("brief");
  const [history,  setHistory]  = useState([]);

  const toggleModel = (id) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.length > 2 ? prev.filter((x) => x !== id) : prev;
      return prev.length < 5 ? [...prev, id] : prev;
    });
  };

  const startRace = async () => {
    if (!brand.trim() || selected.length < 2) return;
    setRacing(true);
    setError(null);
    setResult(null);
    setTab("brief");
    try {
      const resp = await fetch("/api/race", {
        method:  "POST",
        headers: { "Content-Type": "application/json", "x-access-key": accessKey },
        body:    JSON.stringify({ brand, region, model_keys: selected }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `API error ${resp.status}`);
      }
      const data = await resp.json();
      setResult(data);
      setHistory((prev) => {
        const updated = [...prev];
        (data.rankings || []).forEach((r) => {
          const idx = updated.findIndex((h) => h.model_key === r.model_key);
          if (idx >= 0) {
            updated[idx].races++;
            updated[idx].totalScore += r.score.total;
            if (r.model_key === data.winner) updated[idx].wins++;
          } else {
            updated.push({
              model_key:  r.model_key,
              races:      1,
              totalScore: r.score.total,
              wins:       r.model_key === data.winner ? 1 : 0,
            });
          }
        });
        return updated.sort((a, b) => b.wins - a.wins);
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setRacing(false);
    }
  };

  const winner     = result?.rankings?.find((r) => r.model_key === result.winner);
  const winnerMeta = winner ? MODEL_META[winner.model_key] : null;

  return (
    <div style={{ padding: "1.5rem 0" }}>
      {/* Header */}
      <div style={{ marginBottom: "1.75rem" }}>
        <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 4px" }}>
          Biosimilar Surveillance Arena
        </p>
        <p style={{ fontSize: 22, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 4px" }}>The AI Race</p>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0 }}>
          Up to 5 models. One query. The smartest wins the title.
        </p>
      </div>

      {/* Model selector */}
      <div style={{ marginBottom: "1.5rem" }}>
        <ModelSelector selected={selected} onToggle={toggleModel} />
      </div>

      {/* Brand input + region + button */}
      <div style={{ display: "flex", gap: 8, marginBottom: "1.5rem", alignItems: "center" }}>
        <input
          type="text"
          value={brand}
          onChange={(e) => setBrand(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !racing && startRace()}
          placeholder="Enter brand name — e.g. Opdivo, Keytruda, Herceptin..."
          style={{ flex: 1, fontSize: 14 }}
          disabled={racing}
        />
        <select value={region} onChange={(e) => setRegion(e.target.value)} disabled={racing}
                style={{ fontSize: 14, padding: "0.5rem" }}>
          <option value="">Global</option>
          <option value="CEE">CEE</option>
          <option value="LATAM">LATAM</option>
          <option value="MEA">MEA</option>
          <option value="APAC">APAC</option>
        </select>
        <button onClick={startRace} disabled={racing || !brand.trim() || selected.length < 2}
                style={{ whiteSpace: "nowrap", fontSize: 14 }}>
          {racing ? "Racing..." : "Start the Race ↗"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: "0.75rem 1rem", background: "var(--color-background-danger)",
                      border: "0.5px solid var(--color-border-danger)", borderRadius: "var(--border-radius-md)",
                      color: "var(--color-text-danger)", fontSize: 14, marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {/* Racer lanes */}
      {(racing || result) && (
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${selected.length}, minmax(0, 1fr))`, gap: 12, marginBottom: "1.5rem" }}>
          {selected.map((key) => {
            const meta      = MODEL_META[key];
            const rankEntry = result?.rankings?.find((r) => r.model_key === key);
            const isWinner  = result?.winner === key;
            return (
              <div key={key} style={{
                background:  isWinner ? "var(--color-background-secondary)" : "var(--color-background-primary)",
                border:      isWinner ? `1.5px solid ${meta.color}` : "0.5px solid var(--color-border-tertiary)",
                borderLeft:  `3px solid ${meta.color}`,
                borderRadius: "var(--border-radius-lg)",
                padding:     "1rem 1.25rem",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 2 }}>
                  <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", margin: 0 }}>
                    {meta.label}
                  </p>
                  <span style={{
                    display: "inline-block", fontSize: 11, padding: "2px 8px",
                    borderRadius: "var(--border-radius-md)",
                    background:  rankEntry ? "var(--color-background-success)" : "var(--color-background-info)",
                    color:       rankEntry ? "var(--color-text-success)"       : "var(--color-text-info)",
                    border:      `0.5px solid ${rankEntry ? "var(--color-border-success)" : "var(--color-border-info)"}`,
                  }}>
                    {rankEntry ? `${rankEntry.elapsed?.toFixed(1) ?? "?"}s` : "Racing..."}
                  </span>
                </div>
                <p style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 4px" }}>{meta.alias}</p>
                <div style={{ height: 4, background: "var(--color-border-tertiary)", borderRadius: 2, overflow: "hidden", margin: "8px 0" }}>
                  <div style={{
                    height: "100%", borderRadius: 2, background: meta.color,
                    width: rankEntry ? "100%" : "72%",
                    transition: "width 0.6s ease",
                  }} />
                </div>
                {rankEntry && (
                  <>
                    <p style={{ fontSize: 22, fontWeight: 500, color: isWinner ? meta.color : "var(--color-text-primary)", margin: "4px 0 2px" }}>
                      {rankEntry.score?.total ?? 0} pts
                    </p>
                    <p style={{ fontSize: 12, color: "var(--color-text-secondary)", margin: 0 }}>
                      {(rankEntry.output?.pipeline || []).length} developers · {(rankEntry.output?.provenance || []).length} sources
                    </p>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Winner banner */}
      {result && winner && winnerMeta && (
        <div style={{ background: "var(--color-background-secondary)", border: "0.5px solid var(--color-border-tertiary)",
                      borderRadius: "var(--border-radius-lg)", padding: "1.25rem", marginBottom: "1.5rem" }}>
          <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 6px" }}>
            Race complete — champion crowned
          </p>
          <p style={{ fontSize: 20, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 4px" }}>
            ★ {winnerMeta.label} ({winnerMeta.alias}) takes the title — {winner.score?.total} pts
          </p>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 12px" }}>
            {(winner.output?.pipeline || []).length} biosimilar developers
            · {(winner.output?.provenance || []).length} provenance sources
            · {(winner.output?.pipeline || []).filter((p) => p.trial_id && p.trial_id !== "null").length} trial IDs
            · {winner.elapsed?.toFixed(1)}s
            {result.consensus && <span style={{ marginLeft: 8, color: winnerMeta.color, fontWeight: 500 }}>✓ Consensus</span>}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {Object.entries(winner.score?.bd || {}).map(([k, v]) => (
              <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12,
                                     padding: "3px 10px", borderRadius: "var(--border-radius-md)",
                                     background: "var(--color-background-primary)",
                                     border: "0.5px solid var(--color-border-tertiary)",
                                     color: "var(--color-text-secondary)" }}>
                <span style={{ fontWeight: 500, color: "var(--color-text-primary)" }}>{v}</span> {k}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      {result && (
        <>
          <div style={{ display: "flex", gap: 4, marginBottom: 0, borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
            {[["brief", "Winner Brief"], ["all", "All Results"], ["leaderboard", "Session Leaderboard"]].map(([t, label]) => (
              <button key={t} onClick={() => setTab(t)} style={{
                fontSize: 13, padding: "6px 14px",
                borderRadius: "var(--border-radius-md) var(--border-radius-md) 0 0",
                background:   tab === t ? "var(--color-background-secondary)" : "transparent",
                border:       tab === t ? "0.5px solid var(--color-border-tertiary)" : "0.5px solid transparent",
                borderBottom: tab === t ? "1px solid var(--color-background-secondary)" : "none",
                color:        tab === t ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                cursor:       "pointer", marginBottom: -1,
              }}>
                {label}
              </button>
            ))}
          </div>

          {/* Winner Brief tab */}
          {tab === "brief" && winner && (
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
                          borderRadius: "0 var(--border-radius-lg) var(--border-radius-lg) var(--border-radius-lg)", padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.75rem" }}>
                <button
                  onClick={() => exportPDF(result.brand, winnerMeta.alias, formatBrief(winner.output), winner.output?.ai_insight)}
                  style={{ fontSize: 12, padding: "4px 12px", background: "var(--color-background-secondary)",
                           border: "0.5px solid var(--color-border-tertiary)", color: "var(--color-text-secondary)" }}>
                  Export PDF ↓
                </button>
              </div>
              <pre style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.9, whiteSpace: "pre-wrap",
                            color: "var(--color-text-primary)", margin: 0 }}>
                {formatBrief(winner.output)}
              </pre>
              {winner.output?.ai_insight && (
                <div style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)",
                              border: "0.5px solid var(--color-border-tertiary)", padding: "0.75rem 1rem", marginTop: "1rem" }}>
                  <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                              letterSpacing: "0.06em", margin: "0 0 6px", fontWeight: 500 }}>
                    AI Insight — beyond the data
                  </p>
                  <p style={{ fontSize: 13, color: "var(--color-text-primary)", margin: 0, lineHeight: 1.6 }}>
                    {winner.output.ai_insight}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* All Results tab */}
          {tab === "all" && (
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(result.rankings.length, 3)}, minmax(0, 1fr))`,
                          gap: 12, paddingTop: "1rem" }}>
              {result.rankings.map((r) => {
                const meta  = MODEL_META[r.model_key];
                const isWin = r.model_key === result.winner;
                return (
                  <div key={r.model_key} style={{
                    background:   "var(--color-background-primary)",
                    border:       "0.5px solid var(--color-border-tertiary)",
                    borderLeft:   `3px solid ${meta?.color}`,
                    borderRadius: "var(--border-radius-lg)", padding: "1rem",
                  }}>
                    <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                                letterSpacing: "0.06em", margin: "0 0 2px" }}>
                      {meta?.label} — {r.score?.total} pts {isWin && "★"}
                    </p>
                    <p style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 8px" }}>
                      {meta?.alias}
                    </p>
                    {r.error ? (
                      <p style={{ fontSize: 12, color: "var(--color-text-danger)", margin: 0 }}>Error: {r.error}</p>
                    ) : (
                      <div style={{ position: "relative", maxHeight: 320, overflow: "hidden" }}>
                        <pre style={{ fontFamily: "var(--font-mono)", fontSize: 11, lineHeight: 1.7,
                                      whiteSpace: "pre-wrap", color: "var(--color-text-secondary)", margin: 0 }}>
                          {formatBrief(r.output)}
                        </pre>
                        <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 40,
                                      background: "linear-gradient(transparent, var(--color-background-primary))" }} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Session Leaderboard tab */}
          {tab === "leaderboard" && (
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
                          borderRadius: "0 var(--border-radius-lg) var(--border-radius-lg) var(--border-radius-lg)", padding: "1.25rem" }}>
              <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                          letterSpacing: "0.08em", margin: "0 0 12px" }}>
                Session Leaderboard
              </p>
              {history.length === 0 ? (
                <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0 }}>No races yet this session.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: "var(--color-text-secondary)", textAlign: "left" }}>
                      {["Model", "Wins", "Races", "Avg Score"].map((h) => (
                        <th key={h} style={{ paddingBottom: 8, fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h) => {
                      const meta = MODEL_META[h.model_key];
                      return (
                        <tr key={h.model_key} style={{ borderTop: "0.5px solid var(--color-border-tertiary)" }}>
                          <td style={{ padding: "8px 0", color: "var(--color-text-primary)", fontWeight: 500 }}>
                            <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                                           background: meta?.color, marginRight: 8 }} />
                            {meta?.alias}
                          </td>
                          <td style={{ padding: "8px 0", color: h.wins > 0 ? "var(--color-text-primary)" : "var(--color-text-secondary)" }}>
                            {h.wins}
                          </td>
                          <td style={{ padding: "8px 0", color: "var(--color-text-secondary)" }}>{h.races}</td>
                          <td style={{ padding: "8px 0", color: "var(--color-text-secondary)" }}>
                            {Math.round(h.totalScore / h.races)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Race/RacePanel.jsx
git commit -m "feat: complete RacePanel — lanes, winner banner, tabs (Brief/Results/Leaderboard), PDF export"
```

---

## Task 12: App Entry, Styles, Build, and Railway Deployment

**Files:**
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Write `frontend/src/App.jsx`**

```jsx
import RacePanel from "./components/Race/RacePanel.jsx";

const ACCESS_KEY = import.meta.env.VITE_ACCESS_KEY || "";

export default function App() {
  return (
    <div style={{ maxWidth: 1024, margin: "0 auto", padding: "0 1.5rem" }}>
      <RacePanel accessKey={ACCESS_KEY} />
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/index.css`**

```css
:root {
  --color-text-primary:        #1a1a1a;
  --color-text-secondary:      #6b7280;
  --color-text-info:           #1d4ed8;
  --color-text-success:        #15803d;
  --color-text-danger:         #dc2626;
  --color-background-primary:  #ffffff;
  --color-background-secondary:#f9fafb;
  --color-background-info:     #eff6ff;
  --color-background-success:  #f0fdf4;
  --color-background-danger:   #fef2f2;
  --color-border-tertiary:     #e5e7eb;
  --color-border-info:         #bfdbfe;
  --color-border-success:      #bbf7d0;
  --color-border-danger:       #fecaca;
  --border-radius-md:          6px;
  --border-radius-lg:          8px;
  --font-mono:                 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-text-primary:        #f9fafb;
    --color-text-secondary:      #9ca3af;
    --color-text-info:           #93c5fd;
    --color-text-success:        #86efac;
    --color-text-danger:         #fca5a5;
    --color-background-primary:  #111827;
    --color-background-secondary:#1f2937;
    --color-background-info:     #1e3a5f;
    --color-background-success:  #14532d;
    --color-background-danger:   #7f1d1d;
    --color-border-tertiary:     #374151;
    --color-border-info:         #1e40af;
    --color-border-success:      #166534;
    --color-border-danger:       #991b1b;
  }
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--color-background-primary);
  color:       var(--color-text-primary);
  line-height: 1.5;
}

input, select, button {
  font-family: inherit;
  font-size:   14px;
  border-radius: var(--border-radius-md);
  border:      0.5px solid var(--color-border-tertiary);
  background:  var(--color-background-primary);
  color:       var(--color-text-primary);
  padding:     0.5rem 0.75rem;
  outline:     none;
}

input:focus, select:focus {
  border-color: #6366f1;
  box-shadow:   0 0 0 2px rgba(99,102,241,0.2);
}

button {
  cursor:      pointer;
  background:  #6366f1;
  border-color:#6366f1;
  color:       white;
  font-weight: 500;
  transition:  background 0.15s;
}

button:hover:not(:disabled) { background: #4f46e5; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
```

- [ ] **Step 3: Build the frontend**

```bash
cd frontend && npm run build
```

Expected: `frontend/dist/` created with `index.html` and `assets/` folder

- [ ] **Step 4: Verify FastAPI serves the frontend**

```bash
cd ..
ACCESS_KEY=test-key DATABASE_URL=postgresql://x uvicorn main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/ | grep -c "root"
```

Expected: Output `1` (the `<div id="root">` is served)

- [ ] **Step 5: Kill background server**

```bash
pkill -f "uvicorn main:app"
```

- [ ] **Step 6: Run all unit tests to confirm nothing broke**

```bash
pytest tests/test_model_registry.py tests/test_prompt_builder.py tests/test_normalizer.py tests/test_scorer.py tests/test_db_modules.py -v
```

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.jsx frontend/src/index.css
git commit -m "feat: App entry, CSS design tokens (light+dark), frontend build verified"
```

- [ ] **Step 8: Final Railway deployment prep**

Create `.env` from template, fill in real values, then push to Railway:

```bash
# Apply DB schema on Railway postgres
psql $DATABASE_URL -f db/schema_race.sql

# Set Railway environment variables via Railway dashboard or CLI:
# OPENROUTER_API_KEY, ACCESS_KEY, DATABASE_URL, USE_OPENROUTER=true
# ARENA_COST_DAILY_LIMIT_USD=20, ARENA_CACHE_TTL_HOURS=168

# Add Railway build command for frontend
# In Railway: Build Command = "cd frontend && npm install && npm run build"
# Start Command = "uvicorn main:app --host 0.0.0.0 --port $PORT"

git add .
git commit -m "chore: ready for Railway deploy"
git push
```

- [ ] **Step 9: Validate live endpoint**

```bash
curl -X POST https://aiqbiq.com/api/race \
  -H "Content-Type: application/json" \
  -H "x-access-key: $ACCESS_KEY" \
  -d '{"brand":"Opdivo","model_keys":["analyst","scanner"],"region":"CEE"}' | python -m json.tool
```

Expected: JSON response with `winner`, `rankings`, `source: "live"`

---

## Self-Review Against Spec

| Spec requirement | Task covering it |
|---|---|
| 5-model OpenRouter registry | Task 3 |
| Parallel async dispatch, 45s timeout | Task 7 |
| Demo mode (Anthropic API) | Task 7 |
| Prompt builder + region modifiers | Task 4 |
| INN normalization (rapidfuzz) | Task 5 |
| Date → Q+Year normalization | Task 5 |
| Probability clamping | Task 5 |
| Scoring engine (all 7 factors + speed + calibration penalty) | Task 6 |
| Winner declaration + tiebreaker + consensus flag | Task 6 |
| PostgreSQL cache (7-day TTL) | Tasks 2, 8 |
| Daily budget guard ($20 default) | Tasks 2, 8 |
| Audit log | Tasks 2, 8 |
| Auth gate (x-access-key header) | Task 9 |
| POST /api/race endpoint | Task 9 |
| GET /api/health endpoint | Task 9 |
| ModelSelector (2–5 models, toggle cards) | Task 10 |
| Live race lanes (progress bars, elapsed time) | Task 11 |
| Winner banner + score breakdown badges | Task 11 |
| Tabs: Winner Brief / All Results / Session Leaderboard | Task 11 |
| Intelligence brief monospace format | Task 11 |
| AI Insight panel | Task 11 |
| PDF export | Task 11 |
| React 18 + Vite frontend | Tasks 10–12 |
| FastAPI serves built frontend as static files | Task 9, 12 |
| Railway deployment | Task 12 |
| Unit tests for scorer | Task 6 |
| Integration tests for API endpoint | Task 9 |
