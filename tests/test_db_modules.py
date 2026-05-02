import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_pool(fetchrow_return=None):
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    mock_conn.execute  = AsyncMock(return_value=None)
    mock_txn_cm = AsyncMock()
    mock_txn_cm.__aenter__ = AsyncMock(return_value=None)
    mock_txn_cm.__aexit__  = AsyncMock(return_value=False)
    mock_conn.transaction  = MagicMock(return_value=mock_txn_cm)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__  = AsyncMock(return_value=False)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=mock_cm)
    return mock_pool, mock_conn


@pytest.mark.asyncio
async def test_cache_get_miss():
    pool, _ = _mock_pool(fetchrow_return=None)
    with patch("db.connection.get_pool", AsyncMock(return_value=pool)):
        import importlib
        from db import cache
        importlib.reload(cache)
        result = await cache.cache_get("missing_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_calls_execute():
    pool, conn = _mock_pool()
    with patch("db.connection.get_pool", AsyncMock(return_value=pool)):
        import importlib
        from db import cache
        importlib.reload(cache)
        await cache.cache_set("k1", {
            "brand": "Opdivo", "winner": "analyst",
            "winner_score": 80, "winner_data": {},
            "rankings": [], "consensus": False,
            "model_keys": ["analyst"], "region": "",
            "elapsed_s": 2.1,
        })
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_budget_allows_under_limit():
    pool, _ = _mock_pool(fetchrow_return={"total_usd_spent": 5.0})
    with patch("db.connection.get_pool", AsyncMock(return_value=pool)), \
         patch("db.budget.DAILY_LIMIT", 20.0):
        import importlib
        from db import budget
        importlib.reload(budget)
        result = await budget.check_and_record_spend("race", estimated_usd=0.05)
    assert result is True


@pytest.mark.asyncio
async def test_budget_blocks_over_limit():
    pool, _ = _mock_pool(fetchrow_return={"total_usd_spent": 19.99})
    with patch("db.connection.get_pool", AsyncMock(return_value=pool)), \
         patch("db.budget.DAILY_LIMIT", 20.0):
        import importlib
        from db import budget
        importlib.reload(budget)
        result = await budget.check_and_record_spend("race", estimated_usd=0.05)
    assert result is False


@pytest.mark.asyncio
async def test_budget_allows_no_spend_today():
    pool, _ = _mock_pool(fetchrow_return=None)
    with patch("db.connection.get_pool", AsyncMock(return_value=pool)), \
         patch("db.budget.DAILY_LIMIT", 20.0):
        import importlib
        from db import budget
        importlib.reload(budget)
        result = await budget.check_and_record_spend("race", estimated_usd=0.05)
    assert result is True


@pytest.mark.asyncio
async def test_audit_calls_execute():
    pool, conn = _mock_pool()
    with patch("db.connection.get_pool", AsyncMock(return_value=pool)):
        import importlib
        from db import audit
        importlib.reload(audit)
        await audit.log_audit_pg("race", {"brand": "Opdivo"}, {"winner": "analyst"})
    conn.execute.assert_called_once()
