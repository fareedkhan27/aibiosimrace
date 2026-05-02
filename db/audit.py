import json
from datetime import datetime, timezone
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
            datetime.now(timezone.utc),
        )
