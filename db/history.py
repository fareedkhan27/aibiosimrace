import json
from datetime import datetime, timezone
from db.connection import get_pool


async def write_history(result: dict) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO race_history
                (brand, region, model_keys, winner, winner_score,
                 winner_data, rankings, consensus, elapsed_s, raced_at)
            VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8,$9,$10)
            """,
            result.get("brand", ""),
            result.get("region", ""),
            result.get("model_keys", []),
            result.get("winner"),
            result.get("winner_score"),
            json.dumps(result.get("winner_data")),
            json.dumps(result.get("rankings", [])),
            result.get("consensus", False),
            result.get("elapsed_s"),
            datetime.now(timezone.utc),
        )


async def get_history(limit: int = 20, offset: int = 0) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, brand, region, model_keys, winner, winner_score,
                   rankings, consensus, elapsed_s, raced_at
            FROM race_history
            ORDER BY raced_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
    return [
        {
            "id":           r["id"],
            "brand":        r["brand"],
            "region":       r["region"],
            "model_keys":   list(r["model_keys"]),
            "winner":       r["winner"],
            "winner_score": r["winner_score"],
            "rankings":     r["rankings"],
            "consensus":    r["consensus"],
            "elapsed_s":    float(r["elapsed_s"]) if r["elapsed_s"] else None,
            "raced_at":     r["raced_at"].isoformat() if r["raced_at"] else None,
        }
        for r in rows
    ]
