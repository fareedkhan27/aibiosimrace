# Biosimilar AI Race Arena — Production Architecture Blueprint
### Full-Stack · OpenRouter · Model Selection · Real Competition

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [OpenRouter Model Registry](#3-openrouter-model-registry)
4. [Backend: FastAPI Arena Engine](#4-backend-fastapi-arena-engine)
5. [Scoring Engine](#5-scoring-engine)
6. [Frontend: Model Selector + Race UI](#6-frontend-model-selector--race-ui)
7. [Database Schema](#7-database-schema)
8. [Testing Framework](#8-testing-framework)
9. [Demo → Production Migration](#9-demo--production-migration)
10. [Deployment on Railway](#10-deployment-on-railway)
11. [Cost Matrix](#11-cost-matrix)

---

## 1. System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     BIOSIMILAR AI RACE ARENA                            │
│                      Full Production Architecture                        │
│                                                                          │
│  USER                                                                    │
│    │  1. Brand input + model selection                                   │
│    │  2. POST /api/race  { brand, models[], region }                    │
│    ▼                                                                     │
│  FastAPI /api/race                                                       │
│    │                                                                     │
│    ├── Auth gate (x-access-key)                                         │
│    ├── Cache check (PostgreSQL arena_results)                           │
│    ├── Budget check (arena_daily_budget)                                │
│    │                                                                     │
│    ├── Prompt Builder                                                    │
│    │     • Unified extraction prompt                                     │
│    │     • LR region modifier injected                                   │
│    │     • Calibration ladder embedded                                   │
│    │                                                                     │
│    ├── OpenRouter Dispatcher  ← single endpoint, model string routing   │
│    │     ├── anthropic/claude-sonnet-4-5   (The Analyst)                │
│    │     ├── openai/gpt-4o                 (The Hunter)                 │
│    │     ├── google/gemini-2.0-flash-001   (The Scanner)                │
│    │     ├── mistralai/mistral-large       (The Strategist)             │
│    │     └── meta-llama/llama-3.1-70b     (The Challenger)             │
│    │                          [async parallel, 45s timeout each]        │
│    │                                                                     │
│    ├── Normalizer                                                        │
│    │     • INN standardization                                           │
│    │     • Date → Q+Year normalization                                   │
│    │     • Probability clamping                                          │
│    │                                                                     │
│    ├── Scoring Engine                                                    │
│    │     • Developers found         (12 pts each, max 84)               │
│    │     • Provenance sources        (8 pts each, max 40)               │
│    │     • Launch specificity        (6 pts Q+Year, max 30)             │
│    │     • Trial IDs (NCT/CTIS)      (7 pts each, max 35)               │
│    │     • Patent date               (10 pts)                           │
│    │     • Competitor mapping         (3 pts each, max 15)              │
│    │     • AI insight quality        (10 pts)                           │
│    │     • Speed bonus              (10/5/2/0)                          │
│    │     • Calibration penalty      (-20 uncalibrated probability)      │
│    │                                                                     │
│    ├── Winner Declaration                                               │
│    │     • Highest composite score wins                                  │
│    │     • Tiebreaker: provenance depth                                 │
│    │     • Consensus flag: ≥2 models agree on company + year            │
│    │                                                                     │
│    ├── PostgreSQL write (arena_results + audit_log + token_usage)       │
│    └── Response → Frontend                                               │
│                                                                          │
│  FRONTEND                                                                │
│    • Model selector (toggle cards, 2-5 models)                          │
│    • Live race lanes (progress bars, status, elapsed time)              │
│    • Winner reveal + score breakdown                                     │
│    • Tabs: Winner Brief | All Results | Session Leaderboard             │
│    • Intelligence brief in single-liner format                          │
│    • AI Insight panel (beyond-human pattern detection)                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Backend | FastAPI | 0.135.1 | API engine |
| Runtime | Python | 3.11 | Language |
| HTTP Client | httpx | ≥0.27.0 | Async OpenRouter calls |
| Retry | tenacity | ≥8.3.0 | API fault tolerance |
| Fuzzy match | rapidfuzz | ≥3.9.0 | INN normalization |
| DB | PostgreSQL | 15 | Persistent storage |
| DB driver | asyncpg | ≥0.29.0 | Async PG |
| Frontend | React 18 | 18.x | UI |
| Charts | Chart.js | 4.4.0 | Score visualization |
| PDF export | jsPDF | 2.x | Brief export |
| Routing | OpenRouter | v1 | All model calls |
| Hosting | Railway | — | aiqbiq.com |

---

## 3. OpenRouter Model Registry

### `arena/model_registry.py`

```python
"""
All models available for race selection.
id          — internal key used throughout the system
or_id       — OpenRouter model string
label       — display name in UI
alias       — shown to user as "model name"
color       — hex, unique per model
specialty   — one-line shown in UI model card
system      — full system prompt defining extraction persona
cost_tier   — 'high' | 'medium' | 'low' (controls routing logic)
"""

MODEL_REGISTRY = {

    "analyst": {
        "or_id":     "anthropic/claude-sonnet-4-5",
        "label":     "The Analyst",
        "alias":     "Claude Sonnet",
        "color":     "#3266ad",
        "specialty": "Registry-first · NCT/CTIS · Audit-ready",
        "cost_tier": "high",
        "system": """
You are a precision biosimilar intelligence analyst.
Your absolute priority is registry-verified evidence.
Hunt for NCT IDs, CTIS IDs, EMA biosimilar pipeline listings,
FDA Purple Book entries, and WHO prequalification data.
Every pipeline entry must cite a specific verifiable source.
Cross-reference originator USPTO and EPO patent filings to
estimate patent expiry with primary vs secondary patent breakdown.
Note the biosimilar regulatory pathway used (EMA similar
biological medicinal product pathway, FDA 351(k), or national pathway).
You are conservative — never list a developer without evidence.
Return ONLY valid JSON, no markdown, no preamble.
""".strip()
    },

    "hunter": {
        "or_id":     "openai/gpt-4o",
        "label":     "The Hunter",
        "alias":     "GPT-4o",
        "color":     "#0F6E56",
        "specialty": "Launch timing · First-mover · CDMO signals",
        "cost_tier": "high",
        "system": """
You are an aggressive biosimilar market intelligence hunter.
Your mission: maximum developer discovery. Cast the widest possible net.
Look for Phase I programs, CDMO partnerships, licensing deals,
equity filings, and conference disclosures.
Your strength is launch timing prediction: identify which developers
have commercial infrastructure, tender market experience, distribution
partnerships, and regulatory submission readiness.
Prioritize Asian manufacturers (Celltrion, Samsung Bioepis) who may
have launched in Korea or EU before other regions.
Look for interchangeability designation pursuit as ambition signals.
Return ONLY valid JSON, no markdown, no preamble.
""".strip()
    },

    "scanner": {
        "or_id":     "google/gemini-2.0-flash-001",
        "label":     "The Scanner",
        "alias":     "Gemini Flash",
        "color":     "#854F0B",
        "specialty": "Global breadth · Emerging markets · WHO",
        "cost_tier": "low",
        "system": """
You are a global biosimilar surveillance scanner.
Your core advantage is geographic breadth.
Map the complete landscape: CEE (EMA-dependent but national HA required),
LATAM (ANVISA/ANMAT/INVIMA separate pathways, local packaging delays 6-18mo),
MEA (GCC tender cycles Q1/Q3, WHO prequalification as positive signal),
and APAC (PMDA Japan, TGA Australia, NMPA China separate tracks).
Flag biosimilars launched in reference markets not yet in LR markets —
these are the highest near-term risk signals.
Note WHO-prequalified biosimilar manufacturers.
Track indication-specific programs where developers target different indications.
Return ONLY valid JSON, no markdown.
""".strip()
    },

    "strategist": {
        "or_id":     "mistralai/mistral-large",
        "label":     "The Strategist",
        "alias":     "Mistral Large",
        "color":     "#534AB7",
        "specialty": "Market access · Payer logic · Tender cycles",
        "cost_tier": "medium",
        "system": """
You are a biosimilar market access and commercial strategist.
Your unique lens is payer and reimbursement dynamics.
Beyond pipeline tracking, assess which developers have commercial
positioning to win: formulary status in major markets, INN prescribing
policies, mandatory substitution frameworks, government tender wins,
pharmacist substitution uptake.
Flag rebate strategies, risk-sharing agreements, and patient support
programs driving market share.
Assess developer commercial capabilities: own sales force vs distribution.
Note financial sustainability of biosimilar programs.
Return ONLY valid JSON, no markdown.
""".strip()
    },

    "challenger": {
        "or_id":     "meta-llama/llama-3.1-70b-instruct",
        "label":     "The Challenger",
        "alias":     "Llama 3.1 70B",
        "color":     "#993C1D",
        "specialty": "Unconstrained · Maximum scope · API manufacturing",
        "cost_tier": "low",
        "system": """
You are an unconstrained biosimilar intelligence challenger.
Your mandate is maximum completeness without artificial conservatism.
Cast the broadest possible net: every known developer, announced program,
speculated entry, and plausible candidate based on manufacturing capability.
Note when a company has CDMO capabilities to develop a biosimilar even
if no program is publicly announced.
Flag companies that filed patents on biosimilar production processes.
Look at conference abstracts, posters, academic collaborations as
early-stage signals.
Note regulatory signals: IMPD submissions, clinical trial authorizations.
Be aggressive with probability — better to flag a potential entrant
than miss one.
Return ONLY valid JSON, no markdown.
""".strip()
    },
}

# Valid OpenRouter model IDs for reference
OPENROUTER_MODELS = {m["or_id"] for m in MODEL_REGISTRY.values()}
```

---

## 4. Backend: FastAPI Arena Engine

### `arena/client.py` — OpenRouter Dispatcher

```python
import asyncio, json, os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .model_registry import MODEL_REGISTRY

OR_BASE  = os.getenv("OPENROUTER_BASE",  "https://openrouter.ai/api/v1")
OR_KEY   = os.getenv("OPENROUTER_API_KEY", "")
OR_REF   = os.getenv("OPENROUTER_REFERER", "https://aiqbiq.com")
OR_TITLE = os.getenv("OPENROUTER_TITLE",   "AIQBIQ Biosimilar Arena")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
)
async def _call_one(model_key: str, prompt: str, client: httpx.AsyncClient) -> dict:
    meta    = MODEL_REGISTRY[model_key]
    or_id   = meta["or_id"]
    system  = meta["system"]

    try:
        r = await client.post(
            f"{OR_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OR_KEY}",
                "HTTP-Referer":  OR_REF,
                "X-Title":       OR_TITLE,
                "Content-Type":  "application/json",
            },
            json={
                "model":    or_id,
                "messages": [
                    {"role": "system",  "content": system},
                    {"role": "user",    "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens":  2000,
            },
            timeout=45.0,
        )
        r.raise_for_status()
        data    = r.json()
        raw     = data["choices"][0]["message"]["content"]
        clean   = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed  = json.loads(clean)
        return {
            "model_key": model_key,
            "or_id":     or_id,
            "output":    parsed,
            "usage":     data.get("usage", {}),
            "error":     None,
        }
    except json.JSONDecodeError as e:
        return {"model_key": model_key, "or_id": or_id, "output": None, "usage": {}, "error": f"JSON: {e}"}
    except httpx.HTTPStatusError as e:
        return {"model_key": model_key, "or_id": or_id, "output": None, "usage": {}, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"model_key": model_key, "or_id": or_id, "output": None, "usage": {}, "error": str(e)}


async def run_race(prompt: str, model_keys: list[str]) -> list[dict]:
    """
    Fire all selected models in parallel via OpenRouter.
    Return list of results in completion order (not submission order).
    """
    async with httpx.AsyncClient() as client:
        tasks   = [_call_one(k, prompt, client) for k in model_keys]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)
```

### `routes/race.py` — FastAPI Endpoint

```python
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import os, time

from arena.client        import run_race
from arena.prompt_builder import build_race_prompt
from arena.scorer        import score_and_declare_winner
from arena.normalizer    import normalize_outputs
from arena.model_registry import MODEL_REGISTRY
from db.cache            import cache_get, cache_set
from db.audit            import log_audit_pg
from db.budget           import check_and_record_spend

router     = APIRouter()
ACCESS_KEY = os.getenv("ACCESS_KEY", "")


class RaceRequest(BaseModel):
    brand:       str
    model_keys:  list[str]        # keys from MODEL_REGISTRY
    region:      Optional[str] = ""    # CEE | LATAM | MEA | ""
    molecule:    Optional[str] = ""    # INN if known


@router.post("/api/race")
async def race_endpoint(req: RaceRequest, x_access_key: str = Header(default="")):

    # ── Auth ─────────────────────────────────────────────────────────────────
    if x_access_key != ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # ── Validate model selection ──────────────────────────────────────────────
    invalid = [k for k in req.model_keys if k not in MODEL_REGISTRY]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown model keys: {invalid}")
    if not (2 <= len(req.model_keys) <= 5):
        raise HTTPException(status_code=400, detail="Select between 2 and 5 models")

    # ── Cache check ───────────────────────────────────────────────────────────
    cache_key = f"race:{req.brand.lower()}:{':'.join(sorted(req.model_keys))}:{req.region}"
    cached    = await cache_get(cache_key)
    if cached:
        return {**cached, "source": "cache"}

    # ── Budget guard ──────────────────────────────────────────────────────────
    est_cost = len(req.model_keys) * 0.04   # ~$0.04 per model call estimate
    if not await check_and_record_spend("race", estimated_usd=est_cost):
        raise HTTPException(status_code=429, detail="Daily race budget exceeded. Resets UTC midnight.")

    # ── Build prompt ──────────────────────────────────────────────────────────
    prompt = build_race_prompt(
        brand=req.brand,
        region=req.region or "",
        molecule=req.molecule or "",
    )

    # ── Fire race ─────────────────────────────────────────────────────────────
    t_start  = time.time()
    raw      = await run_race(prompt, req.model_keys)
    elapsed  = round(time.time() - t_start, 2)

    # ── Normalize + score ─────────────────────────────────────────────────────
    normalized = normalize_outputs(raw)
    result     = score_and_declare_winner(normalized)

    result["brand"]       = req.brand
    result["region"]      = req.region
    result["model_keys"]  = req.model_keys
    result["elapsed_s"]   = elapsed

    # ── Cache write (7-day TTL) ───────────────────────────────────────────────
    await cache_set(cache_key, result, ttl_hours=168)

    # ── Audit log ─────────────────────────────────────────────────────────────
    await log_audit_pg(
        action="race",
        input_data=req.dict(),
        output_data={
            "winner":         result.get("winner"),
            "winner_score":   result.get("winner_score"),
            "models_run":     len(req.model_keys),
            "elapsed_s":      elapsed,
        }
    )

    return {**result, "source": "live"}
```

---

## 5. Scoring Engine

### `arena/scorer.py`

```python
from datetime import datetime

SCORE_CONFIG = {
    "developer_pts":    12,   "developer_max":  84,
    "provenance_pts":    8,   "provenance_max": 40,
    "launch_q_pts":      6,   "launch_max":     30,
    "trial_id_pts":      7,   "trial_id_max":   35,
    "patent_pts":       10,
    "competitor_pts":    3,   "competitor_max": 15,
    "insight_pts":      10,
    "speed_bonuses":   [10, 5, 2, 0, 0],
    "calib_penalty":   20,    # per uncalibrated probability
}

CALIBRATION = {
    "phase iii":    (35, 90),
    "phase ii":     (10, 40),
    "phase i":       (0, 10),
    "preclinical":   (0, 10),
    "approved":     (55, 85),
    "launched":     (40, 80),
}

def _score_one(data: dict | None) -> dict:
    if not data or not data.get("pipeline"):
        return {"total": 0, "bd": {k: 0 for k in SCORE_CONFIG}, "penalized": 0}

    c    = SCORE_CONFIG
    pipe = data.get("pipeline", [])
    bd   = {}

    bd["developers"]  = min(len(pipe) * c["developer_pts"],   c["developer_max"])
    bd["provenance"]  = min(len(data.get("provenance",[])) * c["provenance_pts"], c["provenance_max"])

    q_yr = sum(1 for p in pipe if p.get("est_launch") and
               __import__("re").match(r"^[QH][1-4]\s*\d{4}", p["est_launch"] or ""))
    bd["launches"]    = min(q_yr * c["launch_q_pts"], c["launch_max"])

    has_id = sum(1 for p in pipe if p.get("trial_id") and p["trial_id"] not in (None, "null", ""))
    bd["trial_ids"]   = min(has_id * c["trial_id_pts"], c["trial_id_max"])

    bd["patent"]      = c["patent_pts"] if (data.get("patent_expiry") and
                         data["patent_expiry"] not in (None, "null", "")) else 0
    bd["competitors"] = min(len(data.get("competitors",[])) * c["competitor_pts"], c["competitor_max"])
    bd["insight"]     = c["insight_pts"] if len(data.get("ai_insight","")) > 60 else 0
    bd["speed"]       = 0   # assigned post-race

    # Calibration penalty
    penalty = 0
    for p in pipe:
        phase = (p.get("phase") or "").lower()
        band  = None
        for key, rng in CALIBRATION.items():
            if key in phase:
                band = rng
                break
        if band:
            prob = int(p.get("probability", 0))
            out  = prob < band[0] or prob > band[1]
            has_note = len(p.get("note","")) > 20
            if out and not has_note:
                penalty += c["calib_penalty"]

    total = sum(bd.values()) - penalty
    return {"total": max(total, 0), "bd": bd, "penalized": penalty}


def score_and_declare_winner(normalized: list[dict]) -> dict:
    scored    = []
    for r in normalized:
        sc = _score_one(r.get("output"))
        scored.append({**r, "score": sc})

    # Speed bonuses — fastest model gets 10 pts
    by_speed = sorted(scored, key=lambda x: x.get("elapsed", 99))
    for i, r in enumerate(by_speed):
        bonus = SCORE_CONFIG["speed_bonuses"][i] if i < len(SCORE_CONFIG["speed_bonuses"]) else 0
        r["score"]["bd"]["speed"] = bonus
        r["score"]["total"]      += bonus

    winner  = max(scored, key=lambda x: x["score"]["total"], default=None)
    runner  = sorted(scored, key=lambda x: x["score"]["total"], reverse=True)

    return {
        "winner":        winner["model_key"] if winner else None,
        "winner_score":  winner["score"]["total"] if winner else 0,
        "winner_data":   winner["output"] if winner else None,
        "rankings":      [
            {
                "model_key": r["model_key"],
                "score":     r["score"],
                "output":    r["output"],
                "elapsed":   r.get("elapsed"),
                "error":     r.get("error"),
            }
            for r in runner
        ],
        "consensus":     _check_consensus(scored),
        "extraction_ts": datetime.utcnow().isoformat(),
    }


def _check_consensus(scored: list[dict]) -> bool:
    """True if ≥2 models independently identified the same lead developer."""
    companies = [
        (r.get("output") or {}).get("pipeline", [{}])[0].get("company","").lower()
        for r in scored
        if (r.get("output") or {}).get("pipeline")
    ]
    if len(companies) < 2:
        return False
    from collections import Counter
    top = Counter(companies).most_common(1)
    return top[0][1] >= 2 if top else False
```

---

## 6. Frontend: Model Selector + Race UI

### `components/Race/ModelSelector.jsx`

```jsx
import { useState } from "react";

const MODELS = [
  { id:"analyst",    label:"The Analyst",    alias:"Claude Sonnet", color:"#3266ad", specialty:"Registry-first · NCT/CTIS · Audit-ready" },
  { id:"hunter",     label:"The Hunter",     alias:"GPT-4o",        color:"#0F6E56", specialty:"Launch timing · First-mover · CDMO signals" },
  { id:"scanner",    label:"The Scanner",    alias:"Gemini Flash",  color:"#854F0B", specialty:"Global breadth · Emerging markets · WHO" },
  { id:"strategist", label:"The Strategist", alias:"Mistral Large", color:"#534AB7", specialty:"Market access · Payer logic · Tender cycles" },
  { id:"challenger", label:"The Challenger", alias:"Llama 3.1 70B", color:"#993C1D", specialty:"Unconstrained · Max scope · Manufacturing signals" },
];

export default function ModelSelector({ selected, onToggle }) {
  return (
    <div>
      <p style={{ fontSize:11, textTransform:"uppercase", letterSpacing:"0.07em",
                  color:"var(--color-text-secondary)", marginBottom:10 }}>
        Select racers — min 2, max 5
      </p>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))", gap:8 }}>
        {MODELS.map(m => {
          const on = selected.includes(m.id);
          return (
            <div
              key={m.id}
              onClick={() => onToggle(m.id)}
              style={{
                cursor:"pointer", userSelect:"none",
                border: on ? `2px solid ${m.color}` : "0.5px solid var(--color-border-tertiary)",
                borderRadius:"var(--border-radius-lg)",
                padding:"0.75rem",
                background: on ? "var(--color-background-secondary)" : "var(--color-background-primary)",
              }}
            >
              <p style={{ fontSize:10, color:"var(--color-text-secondary)", textTransform:"uppercase",
                          letterSpacing:"0.05em", margin:"0 0 2px" }}>{m.label}</p>
              <p style={{ fontSize:13, fontWeight:500, color:"var(--color-text-primary)", margin:"0 0 3px" }}>{m.alias}</p>
              <p style={{ fontSize:11, color:"var(--color-text-secondary)", margin:0, lineHeight:1.4 }}>{m.specialty}</p>
              {on && <p style={{ fontSize:11, color:m.color, margin:"6px 0 0", fontWeight:500 }}>✓ Selected</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

### `components/Race/RacePanel.jsx`

```jsx
import { useState, useRef, useEffect } from "react";
import ModelSelector from "./ModelSelector";

export default function RacePanel({ accessKey }) {
  const [brand,    setBrand]    = useState("");
  const [region,   setRegion]   = useState("");
  const [selected, setSelected] = useState(["analyst","hunter","scanner"]);
  const [racing,   setRacing]   = useState(false);
  const [result,   setResult]   = useState(null);
  const [error,    setError]    = useState(null);
  const [tab,      setTab]      = useState("brief");
  const [history,  setHistory]  = useState([]);    // session leaderboard

  const toggleModel = (id) => {
    setSelected(prev => {
      if (prev.includes(id)) return prev.length > 2 ? prev.filter(x=>x!==id) : prev;
      return prev.length < 5 ? [...prev, id] : prev;
    });
  };

  const startRace = async () => {
    if (!brand.trim() || selected.length < 2) return;
    setRacing(true); setError(null); setResult(null);
    try {
      const resp = await fetch("/api/race", {
        method:  "POST",
        headers: { "Content-Type":"application/json", "x-access-key": accessKey },
        body:    JSON.stringify({ brand, region, model_keys: selected }),
      });
      if (!resp.ok) throw new Error(`API error ${resp.status}`);
      const data = await resp.json();
      setResult(data);
      // Update session leaderboard
      setHistory(prev => {
        const updated = [...prev];
        (data.rankings || []).forEach(r => {
          const idx = updated.findIndex(h => h.model_key === r.model_key);
          if (idx >= 0) {
            updated[idx].races++;
            updated[idx].totalScore += r.score.total;
            if (r.model_key === data.winner) updated[idx].wins++;
          } else {
            updated.push({ model_key:r.model_key, races:1,
                           totalScore:r.score.total, wins: r.model_key===data.winner?1:0 });
          }
        });
        return updated.sort((a,b) => b.wins - a.wins);
      });
    } catch(e) {
      setError(e.message);
    } finally {
      setRacing(false);
    }
  };

  return (
    <div>
      <ModelSelector selected={selected} onToggle={toggleModel} />
      {/* Brand input + region */}
      {/* Racer lanes (dynamic from selected) */}
      {/* Winner banner */}
      {/* Tabs: Brief | All Results | Leaderboard */}
    </div>
  );
}
```

---

## 7. Database Schema

### `db/schema_race.sql`

```sql
-- Race results cache
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

-- Session/historical model performance
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

-- Daily budget tracker
CREATE TABLE IF NOT EXISTS race_daily_budget (
    budget_date     DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    total_usd_spent NUMERIC(8,4) DEFAULT 0,
    call_count      INT DEFAULT 0,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. Testing Framework

### Unit Tests — `tests/test_scorer.py`

```python
import pytest
from arena.scorer import _score_one, score_and_declare_winner

SAMPLE_DATA = {
    "brand":        "Opdivo",
    "inn":          "nivolumab",
    "patent_expiry": "2028-03",
    "competitors":  ["Keytruda (MSD)", "Tecentriq (Roche)"],
    "pipeline": [
        {
            "company":     "Celltrion",
            "indications": ["NSCLC", "Melanoma"],
            "phase":       "Phase III",
            "trial_id":    "NCT04500000",
            "est_launch":  "Q2 2026",
            "markets":     ["KR", "EU"],
            "probability": 65,
            "source":      "ClinicalTrials",
            "note":        "Phase III complete; BLA filing pending"
        },
        {
            "company":     "Samsung Bioepis",
            "indications": ["RCC"],
            "phase":       "Phase II",
            "trial_id":    None,
            "est_launch":  None,
            "markets":     ["KR"],
            "probability": 25,
            "source":      "Company",
            "note":        "Phase II initiated Q3 2024"
        },
    ],
    "provenance": ["ClinicalTrials.gov NCT04500000", "Samsung Bioepis investor report Q4 2024"],
    "ai_insight": "Celltrion's Phase III completion combined with existing commercial infrastructure in EU represents the highest near-term launch risk across all LR regions.",
    "confidence": "Moderate"
}


def test_score_developer_count():
    result = _score_one(SAMPLE_DATA)
    # 2 developers × 12 pts = 24
    assert result["bd"]["developers"] == 24


def test_score_provenance():
    result = _score_one(SAMPLE_DATA)
    # 2 sources × 8 pts = 16
    assert result["bd"]["provenance"] == 16


def test_score_launch_qyear():
    result = _score_one(SAMPLE_DATA)
    # 1 Q+Year launch × 6 pts = 6
    assert result["bd"]["launches"] == 6


def test_score_trial_ids():
    result = _score_one(SAMPLE_DATA)
    # 1 trial ID × 7 pts = 7
    assert result["bd"]["trial_ids"] == 7


def test_score_patent_present():
    result = _score_one(SAMPLE_DATA)
    assert result["bd"]["patent"] == 10


def test_calibration_penalty_clean():
    # Both probabilities within band — no penalty
    result = _score_one(SAMPLE_DATA)
    assert result["penalized"] == 0


def test_calibration_penalty_fires():
    bad_data = {**SAMPLE_DATA, "pipeline": [
        {**SAMPLE_DATA["pipeline"][0], "probability": 5, "note": ""}  # Phase III, prob=5 — below floor 35
    ]}
    result = _score_one(bad_data)
    assert result["penalized"] == 20


def test_winner_declared():
    results = [
        {"model_key": "analyst",  "output": SAMPLE_DATA, "elapsed": 2.1, "error": None},
        {"model_key": "hunter",   "output": None,         "elapsed": 1.5, "error": "timeout"},
    ]
    outcome = score_and_declare_winner(results)
    assert outcome["winner"] == "analyst"


def test_empty_pipeline():
    empty = {**SAMPLE_DATA, "pipeline": []}
    result = _score_one(empty)
    assert result["total"] == 0 or result["bd"]["developers"] == 0
```

### Integration Test — `tests/test_race_api.py`

```python
import pytest
import httpx

BASE = "http://localhost:8000"
KEY  = "test-key"


@pytest.mark.asyncio
async def test_race_returns_winner():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Opdivo", "model_keys": ["analyst","scanner"], "region": "CEE"},
            timeout=90.0,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "winner" in data
    assert data["winner"] in ["analyst", "scanner"]
    assert len(data["rankings"]) == 2


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
async def test_race_caches():
    payload = {"brand": "TestBrand", "model_keys": ["analyst","hunter"], "region": "MEA"}
    async with httpx.AsyncClient() as client:
        r1 = await client.post(f"{BASE}/api/race", headers={"x-access-key": KEY}, json=payload, timeout=90.0)
        r2 = await client.post(f"{BASE}/api/race", headers={"x-access-key": KEY}, json=payload, timeout=10.0)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["source"] == "cache"


@pytest.mark.asyncio
async def test_race_auth_required():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            json={"brand": "Opdivo", "model_keys": ["analyst","hunter"], "region": ""},
        )
    assert resp.status_code == 401
```

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx --break-system-packages

# Unit tests (no network)
pytest tests/test_scorer.py -v

# Integration tests (requires running server + valid API keys)
ACCESS_KEY=test-key uvicorn main:app --reload &
pytest tests/test_race_api.py -v --asyncio-mode=auto
```

---

## 9. Demo → Production Migration

### What changes when moving from demo (Anthropic-only) to production (OpenRouter)

| Component | Demo Mode | Production Mode |
|---|---|---|
| Model calls | All → Anthropic API (different personas) | Each → correct model via OpenRouter |
| API key | `ANTHROPIC_API_KEY` | `OPENROUTER_API_KEY` |
| Endpoint | `api.anthropic.com/v1/messages` | `openrouter.ai/api/v1/chat/completions` |
| Request format | Anthropic messages format | OpenAI-compatible (OpenRouter) |
| Response format | `data.content[0].text` | `data.choices[0].message.content` |
| Model string | `claude-sonnet-4-20250514` | `anthropic/claude-sonnet-4-5` |
| Cost | ~$3/1M tokens (single model) | Per-model rate (see §11) |
| Competitive validity | Same LLM, different instructions | Genuinely different models |

### Environment toggle

```python
# config.py
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "false").lower() == "true"

# In arena/client.py
if USE_OPENROUTER:
    base = OPENROUTER_BASE
    key  = OPENROUTER_API_KEY
    headers = {"Authorization": f"Bearer {key}", "HTTP-Referer": OR_REF}
    payload_key = "model"   # OpenRouter model string
else:
    base = "https://api.anthropic.com/v1"
    key  = ANTHROPIC_API_KEY
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    payload_key = "model"   # Anthropic model string
```

### `.env` — Production

```bash
USE_OPENROUTER=true
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE=https://openrouter.ai/api/v1
OPENROUTER_REFERER=https://aiqbiq.com
OPENROUTER_TITLE=AIQBIQ Biosimilar Arena
ARENA_COST_DAILY_LIMIT_USD=20
ARENA_CACHE_TTL_HOURS=168
```

---

## 10. Deployment on Railway

### Deployment Steps

```bash
# 1. Add OpenRouter key to Railway environment
#    Settings → Variables → OPENROUTER_API_KEY

# 2. Run schema migration
psql $DATABASE_URL -f db/schema_race.sql

# 3. Register new route in main.py
from routes.race import router as race_router
app.include_router(race_router)

# 4. Deploy
git add . && git commit -m "feat: biosimilar race arena endpoint" && git push

# 5. Validate
curl -X POST https://aiqbiq.com/api/race \
  -H "Content-Type: application/json" \
  -H "x-access-key: $ACCESS_KEY" \
  -d '{"brand":"Opdivo","model_keys":["analyst","scanner"],"region":"CEE"}'
```

### Health Check Extension

```python
@app.get("/api/health")
async def health():
    return {
        "status":       "ok",
        "db_type":      "postgresql",
        "race_arena":   "enabled",
        "models_available": list(MODEL_REGISTRY.keys()),
        "openrouter":   bool(os.getenv("OPENROUTER_API_KEY")),
    }
```

---

## 11. Cost Matrix

### Per-Model Cost (OpenRouter, approximate)

| Model | Input $/1M | Output $/1M | Per race call est. |
|---|---|---|---|
| Claude Sonnet | $3.00 | $15.00 | ~$0.012 |
| GPT-4o | $2.50 | $10.00 | ~$0.010 |
| Gemini 2.0 Flash | $0.10 | $0.40 | ~$0.001 |
| Mistral Large | $2.00 | $6.00 | ~$0.008 |
| Llama 3.1 70B | $0.30 | $0.40 | ~$0.002 |

### Race Cost Scenarios

| Config | Models | Est. Cost |
|---|---|---|
| Minimum (2 models) | Claude + Gemini | ~$0.013 |
| Standard (3 models) | Claude + GPT-4o + Gemini | ~$0.023 |
| Full field (5 models) | All five | ~$0.033 |
| Full 37-market sweep × 3 models | 37 runs | ~$0.85 |

**Daily budget recommendation:** `ARENA_COST_DAILY_LIMIT_USD=20`
At $0.033/run (5 models), this allows ~600 races per day.

---

*Biosimilar AI Race Arena — Production Blueprint v1.0*
*AIQBIQ | aiqbiq.com | CEE · LATAM · MEA*
