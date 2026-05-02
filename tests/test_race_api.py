import pytest
import httpx

BASE = "http://localhost:8000"
KEY  = "test-key"


@pytest.mark.asyncio
async def test_race_auth_required():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            json={"brand": "Opdivo", "model_keys": ["analyst", "hunter"], "region": ""},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_race_model_validation():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Keytruda", "model_keys": ["unknown_model"], "region": ""},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_race_min_models():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Opdivo", "model_keys": ["analyst"], "region": ""},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_race_max_models():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={
                "brand": "Opdivo",
                "model_keys": ["analyst", "hunter", "scanner", "strategist", "challenger", "analyst"],
                "region": "",
            },
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "analyst" in data["models_available"]


@pytest.mark.asyncio
async def test_race_returns_winner():
    """Requires running server with valid API keys."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/api/race",
            headers={"x-access-key": KEY},
            json={"brand": "Opdivo", "model_keys": ["analyst", "scanner"], "region": "CEE"},
            timeout=90.0,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "winner" in data
    assert data["winner"] in ["analyst", "scanner"]
    assert len(data["rankings"]) == 2
    assert data["source"] in ("live", "cache")


@pytest.mark.asyncio
async def test_race_caches():
    payload = {"brand": "TestBrandXYZ999", "model_keys": ["analyst", "hunter"], "region": "MEA"}
    async with httpx.AsyncClient() as client:
        r1 = await client.post(f"{BASE}/api/race", headers={"x-access-key": KEY}, json=payload, timeout=90.0)
        r2 = await client.post(f"{BASE}/api/race", headers={"x-access-key": KEY}, json=payload, timeout=10.0)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["source"] == "cache"
