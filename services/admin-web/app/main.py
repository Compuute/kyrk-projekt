from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as html_router


def create_app() -> FastAPI:
    app = FastAPI(title="admin-web", version="0.1.0")
    app.include_router(html_router)

    from pathlib import Path

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


app = create_app()
