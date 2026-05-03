import os
from fastapi import APIRouter, HTTPException, Header

from db.history import get_history

router     = APIRouter()
ACCESS_KEY = os.getenv("ACCESS_KEY", "")


@router.get("/api/history")
async def history_endpoint(
    limit:        int = 20,
    offset:       int = 0,
    x_access_key: str = Header(default=""),
):
    if x_access_key != ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    items = await get_history(limit=min(limit, 100), offset=offset)
    return {"items": items, "limit": limit, "offset": offset}
