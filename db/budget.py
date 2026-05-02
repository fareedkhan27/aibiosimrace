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
