import os
import time
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from arena.client          import run_race
from arena.prompt_builder  import build_race_prompt
from arena.scorer          import score_and_declare_winner
from arena.normalizer      import normalize_outputs
from arena.model_registry  import MODEL_REGISTRY
from db.cache              import cache_get, cache_set
from db.audit              import log_audit_pg
from db.budget             import check_and_record_spend

router     = APIRouter()
ACCESS_KEY = os.getenv("ACCESS_KEY", "")


class RaceRequest(BaseModel):
    brand:      str
    model_keys: list[str]
    region:     Optional[str] = ""
    molecule:   Optional[str] = ""


@router.post("/api/race")
async def race_endpoint(req: RaceRequest, x_access_key: str = Header(default="")):

    if x_access_key != ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    invalid = [k for k in req.model_keys if k not in MODEL_REGISTRY]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown model keys: {invalid}")
    if not (2 <= len(req.model_keys) <= 5):
        raise HTTPException(status_code=400, detail="Select between 2 and 5 models")

    cache_key = f"race:{req.brand.lower()}:{':'.join(sorted(req.model_keys))}:{req.region}"
    cached    = await cache_get(cache_key)
    if cached:
        return {**cached, "source": "cache"}

    est_cost = len(req.model_keys) * 0.04
    if not await check_and_record_spend("race", estimated_usd=est_cost):
        raise HTTPException(status_code=429, detail="Daily race budget exceeded. Resets UTC midnight.")

    prompt  = build_race_prompt(brand=req.brand, region=req.region or "", molecule=req.molecule or "")
    t_start = time.time()
    raw     = await run_race(prompt, req.model_keys)
    elapsed = round(time.time() - t_start, 2)

    normalized = normalize_outputs(raw)
    result     = score_and_declare_winner(normalized)

    result["brand"]      = req.brand
    result["region"]     = req.region
    result["model_keys"] = req.model_keys
    result["elapsed_s"]  = elapsed

    await cache_set(cache_key, result, ttl_hours=168)
    await log_audit_pg(
        action="race",
        input_data=req.model_dump(),
        output_data={
            "winner":       result.get("winner"),
            "winner_score": result.get("winner_score"),
            "models_run":   len(req.model_keys),
            "elapsed_s":    elapsed,
        },
    )

    return {**result, "source": "live"}
