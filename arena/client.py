import asyncio
import json
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .model_registry import MODEL_REGISTRY
from config import (
    USE_OPENROUTER,
    OPENROUTER_BASE, OPENROUTER_API_KEY, OPENROUTER_REFERER, OPENROUTER_TITLE,
    ANTHROPIC_API_KEY, ANTHROPIC_DEMO_MODEL,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
)
async def _call_openrouter(model_key: str, prompt: str, client: httpx.AsyncClient) -> dict:
    meta = MODEL_REGISTRY[model_key]
    t0   = time.time()
    try:
        r = await client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer":  OPENROUTER_REFERER,
                "X-Title":       OPENROUTER_TITLE,
                "Content-Type":  "application/json",
            },
            json={
                "model":    meta["or_id"],
                "messages": [
                    {"role": "system", "content": meta["system"]},
                    {"role": "user",   "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens":  2000,
            },
            timeout=45.0,
        )
        r.raise_for_status()
        data  = r.json()
        raw   = data["choices"][0]["message"]["content"]
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return {
            "model_key": model_key, "or_id": meta["or_id"],
            "output": json.loads(clean), "usage": data.get("usage", {}),
            "error": None, "elapsed": round(time.time() - t0, 2),
        }
    except json.JSONDecodeError as e:
        return {"model_key": model_key, "or_id": meta["or_id"], "output": None, "usage": {},
                "error": f"JSON: {e}", "elapsed": round(time.time() - t0, 2)}
    except httpx.HTTPStatusError as e:
        return {"model_key": model_key, "or_id": meta["or_id"], "output": None, "usage": {},
                "error": f"HTTP {e.response.status_code}", "elapsed": round(time.time() - t0, 2)}
    except Exception as e:
        return {"model_key": model_key, "or_id": meta["or_id"], "output": None, "usage": {},
                "error": str(e), "elapsed": round(time.time() - t0, 2)}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
)
async def _call_anthropic_demo(model_key: str, prompt: str, client: httpx.AsyncClient) -> dict:
    meta = MODEL_REGISTRY[model_key]
    t0   = time.time()
    try:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type":      "application/json",
            },
            json={
                "model":      ANTHROPIC_DEMO_MODEL,
                "max_tokens": 2000,
                "system":     meta["system"],
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=45.0,
        )
        r.raise_for_status()
        data  = r.json()
        raw   = (data.get("content") or [{}])[0].get("text", "{}")
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return {
            "model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL,
            "output": json.loads(clean), "usage": data.get("usage", {}),
            "error": None, "elapsed": round(time.time() - t0, 2),
        }
    except json.JSONDecodeError as e:
        return {"model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL, "output": None, "usage": {},
                "error": f"JSON: {e}", "elapsed": round(time.time() - t0, 2)}
    except httpx.HTTPStatusError as e:
        return {"model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL, "output": None, "usage": {},
                "error": f"HTTP {e.response.status_code}", "elapsed": round(time.time() - t0, 2)}
    except Exception as e:
        return {"model_key": model_key, "or_id": ANTHROPIC_DEMO_MODEL, "output": None, "usage": {},
                "error": str(e), "elapsed": round(time.time() - t0, 2)}


async def run_race(prompt: str, model_keys: list[str]) -> list[dict]:
    call_fn = _call_openrouter if USE_OPENROUTER else _call_anthropic_demo
    async with httpx.AsyncClient() as client:
        tasks   = [call_fn(k, prompt, client) for k in model_keys]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)
