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
              AND expires_at > NOW()
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
