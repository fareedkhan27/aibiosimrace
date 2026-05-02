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
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '168 hours'),
    elapsed_s       NUMERIC(6,2)
);

CREATE INDEX IF NOT EXISTS idx_race_brand  ON race_results (brand);
CREATE INDEX IF NOT EXISTS idx_race_winner ON race_results (winner);
CREATE INDEX IF NOT EXISTS idx_race_ts     ON race_results (extraction_ts DESC);

CREATE INDEX IF NOT EXISTS idx_race_expires
    ON race_results (expires_at)
    WHERE expires_at IS NOT NULL;

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

CREATE INDEX IF NOT EXISTS idx_lb_model_ts
    ON model_leaderboard (model_key, race_ts DESC);

-- Daily budget tracker (one row per UTC date)
CREATE TABLE IF NOT EXISTS race_daily_budget (
    budget_date     DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    total_usd_spent NUMERIC(8,4) NOT NULL DEFAULT 0,
    call_count      INT NOT NULL DEFAULT 0,
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
