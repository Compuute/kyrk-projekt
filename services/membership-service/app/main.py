"""FastAPI app factory for membership-service.

In production the real adapters (PropelAuth, Firestore, Cloud KMS) are wired
in `deps.py`. The factory here stays minimal so tests can import it without
side effects.
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_members import router as members_router


def create_app() -> FastAPI:
    app = FastAPI(title="membership-service", version="0.1.0")
    app.include_router(members_router)

    @app.get("/healthz", tags=["infra"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
