# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository is currently in the **design/specification phase**. The two existing files are:
- `biosimilar_arena_architecture.md` — full production architecture blueprint (source of truth)
- `biosimilar_ai_race.html` — standalone demo/prototype UI

No backend or frontend source directories exist yet. Implementation follows the blueprint in `biosimilar_arena_architecture.md`.

## What This Builds

**Biosimilar AI Race Arena** — a platform where 2–5 LLMs compete in parallel to extract biosimilar drug pipeline intelligence (developers, trial IDs, launch timings, patent expiry) for a given brand drug. Models race to return the highest-scoring structured JSON. Deployed at `aiqbiq.com`.

## Planned Commands

Once implemented, these commands apply:

```bash
# Install Python deps
pip install fastapi uvicorn httpx tenacity rapidfuzz asyncpg pytest pytest-asyncio

# Run dev server (demo mode, no OpenRouter)
uvicorn main:app --reload

# Run dev server (production mode with OpenRouter)
USE_OPENROUTER=true OPENROUTER_API_KEY=sk-or-... ACCESS_KEY=test-key uvicorn main:app --reload

# Apply DB schema
psql $DATABASE_URL -f db/schema_race.sql

# Unit tests (no network required)
pytest tests/test_scorer.py -v

# Integration tests (requires running server)
pytest tests/test_race_api.py -v --asyncio-mode=auto
```

## Architecture

### Request Flow
```
POST /api/race { brand, model_keys[], region }
  → Auth gate (x-access-key header)
  → Cache check (PostgreSQL race_results, 7-day TTL)
  → Budget guard (race_daily_budget table, default $20/day)
  → Prompt builder (brand + region modifier + calibration ladder)
  → OpenRouter dispatcher (all models fired in parallel, 45s timeout, 3 retries)
  → Normalizer (INN standardization, date → Q+Year, probability clamping)
  → Scoring engine → winner declaration
  → Cache write + audit log
  → Response to frontend
```

### File Structure (to be implemented)
```
arena/
  model_registry.py   — 5 model definitions with OpenRouter IDs + system prompts
  client.py           — async OpenRouter dispatcher with tenacity retries
  prompt_builder.py   — unified extraction prompt + region modifier injection
  scorer.py           — multi-factor scoring + winner declaration
  normalizer.py       — INN standardization via rapidfuzz, date normalization
routes/
  race.py             — FastAPI POST /api/race endpoint
db/
  schema_race.sql     — 3 tables: race_results, model_leaderboard, race_daily_budget
  cache.py            — cache_get / cache_set (PostgreSQL-backed)
  audit.py            — audit log writer
  budget.py           — daily spend check + increment
tests/
  test_scorer.py      — unit tests for scoring logic (no network)
  test_race_api.py    — integration tests against running server
components/Race/
  ModelSelector.jsx   — toggle cards for model selection (2–5, enforced)
  RacePanel.jsx       — main race UI: lanes, results tabs, leaderboard
```

### The 5 Racers (MODEL_REGISTRY keys)
| Key | Alias | OpenRouter ID | Specialty |
|---|---|---|---|
| `analyst` | Claude Sonnet | `anthropic/claude-sonnet-4-5` | Registry-first, NCT/CTIS, audit-ready |
| `hunter` | GPT-4o | `openai/gpt-4o` | Launch timing, first-mover, CDMO signals |
| `scanner` | Gemini Flash | `google/gemini-2.0-flash-001` | Global breadth, emerging markets, WHO |
| `strategist` | Mistral Large | `mistralai/mistral-large` | Market access, payer logic, tender cycles |
| `challenger` | Llama 3.1 70B | `meta-llama/llama-3.1-70b-instruct` | Unconstrained, max scope |

### Scoring Engine (`arena/scorer.py`)
Points are additive; winner = highest composite score. Key factors:
- **Developers found**: 12 pts each (max 84)
- **Provenance sources**: 8 pts each (max 40)
- **Launch specificity** (Q+Year format): 6 pts each (max 30)
- **Trial IDs** (NCT/CTIS): 7 pts each (max 35)
- **Patent date present**: 10 pts
- **Competitor mapping**: 3 pts each (max 15)
- **AI insight** (>60 chars): 10 pts
- **Speed bonus**: 10/5/2/0 pts for 1st–4th to finish
- **Calibration penalty**: −20 pts per probability outside its phase band (e.g., Phase III must be 35–90%)

Tiebreaker: provenance depth. Consensus flag fires when ≥2 models independently name the same lead developer.

### Demo → Production Toggle
The `USE_OPENROUTER` env var switches between demo mode (single Anthropic API, different system prompts) and production mode (true multi-model via OpenRouter). See §9 of the architecture doc for the exact API format differences.

## Environment Variables
```
OPENROUTER_API_KEY        — required in production
ACCESS_KEY                — header auth for all /api/* endpoints
USE_OPENROUTER            — "true" for production, "false" for demo
ARENA_COST_DAILY_LIMIT_USD — default 20 (allows ~600 full-field races/day)
ARENA_CACHE_TTL_HOURS     — default 168 (7 days)
DATABASE_URL              — PostgreSQL connection string
```

## Cost Reference
- Minimum race (2 models: Claude + Gemini): ~$0.013
- Standard race (3 models): ~$0.023
- Full race (all 5 models): ~$0.033
- Budget ceiling $20/day → ~600 full-field races
