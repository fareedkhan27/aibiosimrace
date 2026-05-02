import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_or_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 500},
    }
    mock.raise_for_status = MagicMock()
    return mock


def _make_anth_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "content": [{"text": json.dumps(payload)}],
        "usage": {"input_tokens": 100, "output_tokens": 500},
    }
    mock.raise_for_status = MagicMock()
    return mock


def _make_mock_client(response):
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


@pytest.mark.asyncio
async def test_run_race_openrouter_returns_keys():
    payload = {"pipeline": [], "provenance": []}
    mock_cm = _make_mock_client(_make_or_response(payload))

    with patch("arena.client.USE_OPENROUTER", True), \
         patch("httpx.AsyncClient", return_value=mock_cm):
        from arena import client as c
        import importlib; importlib.reload(c)
        results = await c.run_race("test prompt", ["analyst", "scanner"])

    assert len(results) == 2
    assert {r["model_key"] for r in results} == {"analyst", "scanner"}


@pytest.mark.asyncio
async def test_run_race_includes_elapsed():
    payload = {"pipeline": [], "provenance": []}
    mock_cm = _make_mock_client(_make_or_response(payload))

    with patch("arena.client.USE_OPENROUTER", True), \
         patch("httpx.AsyncClient", return_value=mock_cm):
        from arena import client as c
        import importlib; importlib.reload(c)
        results = await c.run_race("test prompt", ["analyst"])

    assert "elapsed" in results[0]
    assert isinstance(results[0]["elapsed"], float)


@pytest.mark.asyncio
async def test_run_race_anthropic_demo():
    payload = {"pipeline": [], "provenance": []}
    mock_cm = _make_mock_client(_make_anth_response(payload))

    with patch("arena.client.USE_OPENROUTER", False), \
         patch("httpx.AsyncClient", return_value=mock_cm):
        from arena import client as c
        import importlib; importlib.reload(c)
        results = await c.run_race("test prompt", ["analyst"])

    assert len(results) == 1
    assert results[0]["output"] == payload


@pytest.mark.asyncio
async def test_run_race_error_captured():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("network error"))
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("arena.client.USE_OPENROUTER", True), \
         patch("httpx.AsyncClient", return_value=mock_cm):
        from arena import client as c
        import importlib; importlib.reload(c)
        # Patch retry to not retry (speed up test)
        with patch.object(c._call_openrouter, 'retry', None):
            pass
        results = await c.run_race("test prompt", ["analyst"])

    assert results[0]["output"] is None
    assert results[0]["error"] is not None
