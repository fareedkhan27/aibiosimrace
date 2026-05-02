import asyncio
import asyncpg
from config import DATABASE_URL

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    global _pool
    async with _pool_lock:
        if _pool is None:
            if not DATABASE_URL:
                raise RuntimeError("DATABASE_URL is not set — cannot initialize connection pool")
            _pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=2,
                max_size=10,
            )
    return _pool


async def close_pool() -> None:
    global _pool
    async with _pool_lock:
        if _pool:
            await _pool.close()
            _pool = None
