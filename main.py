import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes.race       import router as race_router
from db.connection     import get_pool, close_pool
from arena.model_registry import MODEL_REGISTRY


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_pool()
    except Exception as exc:  # noqa: BLE001
        # Allow the server to start even when the DB is unreachable
        # (e.g. demo mode or CI).  DB calls inside route handlers will
        # fail individually rather than preventing startup.
        import logging
        logging.getLogger(__name__).warning("DB pool not initialised at startup: %s", exc)
    yield
    await close_pool()


app = FastAPI(title="Biosimilar AI Race Arena", lifespan=lifespan)
app.include_router(race_router)


@app.get("/api/health")
async def health():
    return {
        "status":           "ok",
        "db_type":          "postgresql",
        "race_arena":       "enabled",
        "models_available": list(MODEL_REGISTRY.keys()),
        "openrouter":       bool(os.getenv("OPENROUTER_API_KEY")),
    }


_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    _assets = os.path.join(_frontend_dist, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
