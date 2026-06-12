"""FastAPI app factory for membership-service.

In production the real adapters (Zitadel, Firestore, Cloud KMS) are wired
in `deps.py`. The factory here stays minimal so tests can import it without
side effects.
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_members import router as members_router
from app.api.routes_funerals import router as funerals_router
from app.api.routes_sunday_school import router as sunday_school_router


def create_app() -> FastAPI:
    app = FastAPI(title="membership-service", version="0.1.0")
    app.include_router(members_router)
    app.include_router(funerals_router)
    app.include_router(sunday_school_router)

    @app.get("/healthz", tags=["infra"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
