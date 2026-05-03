# Biosimilar AI Race Arena

A competitive intelligence platform where 2–5 large language models race in parallel to extract biosimilar drug pipeline data for any reference biologic. Models are scored, ranked, and a winner is declared in real time.

Live at **[aiqbiq.com](https://aiqbiq.com)**

---

## What it does

Enter a brand drug name (Opdivo, Herceptin, Humira…). Select 2–5 AI models. They race simultaneously to extract:

- All known biosimilar developers and their clinical trial phase
- Trial IDs (NCT / CTIS), estimated launch dates (Q+Year format), target markets
- Patent expiry, mechanism of action, originator details
- Provenance citations for every claim — no hallucinations allowed
- Launched and approved biosimilars split by **US / EU** and **Rest of World**

Each model's response is scored across 8 factors. The highest-scoring model wins. A consensus flag fires when ≥2 models independently identify the same lead developer. Every live race is saved to a persistent **Race History** log.

---

## The 5 Racers

| Key | Alias | Model | Specialty |
|---|---|---|---|
| `analyst` | The Analyst | Claude Sonnet | Registry-first, NCT/CTIS, audit-ready |
| `hunter` | The Hunter | GPT-4o | Launch timing, first-mover, CDMO signals |
| `scanner` | The Scanner | Gemini Flash | Global breadth, emerging markets, WHO |
| `strategist` | The Strategist | Mistral Large | Market access, payer logic, tender cycles |
| `challenger` | The Challenger | Llama 3.1 70B | Unconstrained, maximum scope |

---

## Scoring

Points are additive. Winner = highest composite score.

| Factor | Points | Cap |
|---|---|---|
| Developers found | 12 pts each | 84 |
| Provenance sources | 8 pts each | 40 |
| Launch specificity (Q+Year) | 6 pts each | 30 |
| Trial IDs (NCT/CTIS) | 7 pts each | 35 |
| Patent date present | 10 pts | — |
| Competitor mapping | 3 pts each | 15 |
| AI insight (>60 chars) | 10 pts | — |
| Speed bonus (1st–4th) | 10 / 5 / 2 / 0 | — |
| Calibration penalty | −20 pts per out-of-band probability | — |

Tiebreaker: provenance depth. Probability bands are enforced per phase (e.g. Phase III must be 35–75%).

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI 0.135.1 |
| API dispatch | httpx + tenacity (3 retries, exponential backoff) |
| Models | OpenRouter (production) / Anthropic API (demo) |
| Normalisation | rapidfuzz (INN fuzzy match), custom date → Q+Year |
| Database | PostgreSQL 15 via asyncpg |
| Frontend | React 18 + Vite 5 |
| PDF export | jsPDF (multi-page) |
| Deployment | Railway |

---

## Running locally

### Prerequisites

- Python 3.11+, Node 18+, PostgreSQL 15

### 1. Clone and install

```bash
git clone https://github.com/fareedkhan27/aibiosimrace.git
cd aibiosimrace
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

### 2. Configure environment

Create a `.env` file in the project root:

```
USE_OPENROUTER=false          # true for production multi-model
ANTHROPIC_API_KEY=sk-ant-...  # demo mode: single Anthropic key
OPENROUTER_API_KEY=sk-or-...  # production mode: OpenRouter key
ACCESS_KEY=your-secret-here
DATABASE_URL=postgresql://localhost/biosim_arena
```

> **Access key:** The frontend prompts for the access key on first visit and saves it to `localStorage`. No build-time env var is needed for the frontend — just set `ACCESS_KEY` on the backend.

### 3. Initialise database

```bash
createdb biosim_arena
psql biosim_arena -f db/schema_race.sql
```

### 4. Start

```bash
uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000). Enter your `ACCESS_KEY` when prompted.

### Frontend hot reload (optional)

```bash
# Terminal 1
uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev   # http://localhost:5173
```

### Run tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Execution modes

| Mode | `USE_OPENROUTER` | How it works |
|---|---|---|
| Demo | `false` | All models → Anthropic API with different system prompts. One key needed. |
| Production | `true` | Each model → its own endpoint via OpenRouter. True multi-model race. |

---

## API

### `POST /api/race`

Headers: `x-access-key: <ACCESS_KEY>`, `Content-Type: application/json`

```json
{
  "brand": "Opdivo",
  "model_keys": ["analyst", "hunter", "scanner"],
  "region": "CEE"
}
```

`model_keys`: 2–5 values from `analyst | hunter | scanner | strategist | challenger`  
`region`: optional — `CEE | LATAM | MEA | APAC` or omit for global

**Response** includes `winner`, `winner_score`, `rankings` (scored per model), `consensus` flag, full pipeline data, and `source` (`live` or `cache`).

### `GET /api/history`

Returns the 20 most recent live races (cache hits are not recorded).

Headers: `x-access-key: <ACCESS_KEY>`

Query params: `limit` (max 100, default 20), `offset` (default 0)

```json
{
  "items": [
    {
      "id": 1,
      "brand": "Opdivo",
      "region": "",
      "model_keys": ["analyst", "hunter", "scanner"],
      "winner": "analyst",
      "winner_score": 145,
      "rankings": [...],
      "consensus": false,
      "elapsed_s": 11.4,
      "raced_at": "2026-05-03T10:30:00+00:00"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

### `GET /api/health`

Returns `{"status": "ok"}` plus model list and DB/OpenRouter status.

---

## Deploying to Railway

1. Fork or push this repo to GitHub
2. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Add a **PostgreSQL** database service in the same project
4. Set environment variables on the app service:

| Variable | Value |
|---|---|
| `USE_OPENROUTER` | `true` |
| `OPENROUTER_API_KEY` | your key |
| `ACCESS_KEY` | your secret |
| `DATABASE_URL` | auto-set by Railway Postgres service |
| `ARENA_COST_DAILY_LIMIT_USD` | `20` |

> No `VITE_ACCESS_KEY` needed — the frontend prompts for the key at first visit and persists it in the browser.

5. Railway auto-detects `nixpacks.toml` — no build command needed. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Apply schema once via Railway's Postgres query tab:
   ```sql
   -- paste contents of db/schema_race.sql
   ```
7. Add custom domain `aiqbiq.com` → point your DNS CNAME to the Railway-provided value

---

## Cost reference

| Race | Models | Est. cost |
|---|---|---|
| Minimum | 2 (Claude + Gemini) | ~$0.013 |
| Standard | 3 models | ~$0.023 |
| Full field | 5 models | ~$0.033 |

Default budget ceiling: $20/day (~600 full-field races). Configurable via `ARENA_COST_DAILY_LIMIT_USD`.

Results are cached for 7 days per brand + model combination. Cache hits do not count against the daily budget.

---

## Data persistence

| Store | What's saved | Overwritten? |
|---|---|---|
| `race_results` | Last result per brand + model set | Yes — 7-day cache, upserts on conflict |
| `race_history` | Every live race, append-only | Never — full history log |
| `audit_log` | Summary of every race (winner, score, elapsed) | Never |
| `race_daily_budget` | Daily spend tracker | Resets at UTC midnight |

The **Race History** section in the UI loads automatically and shows the 20 most recent races.

---

## Project structure

```
arena/          model registry, prompt builder, client, normalizer, scorer
db/             schema, connection pool, cache, history, audit log, budget guard
routes/         POST /api/race, GET /api/history endpoints
frontend/src/   React app — ModelSelector, RacePanel, App
tests/          unit + integration tests
nixpacks.toml   Railway build config (Python-only)
```

---

## License

MIT
