from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_intake import router as intake_router
from app.api.routes_submissions import router as submissions_router

_DEFAULT_ORIGINS = [
    "https://kyrka-portal.pages.dev",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]


def create_app() -> FastAPI:
    app = FastAPI(title="membership-intake", version="0.1.0")

    origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else _DEFAULT_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.include_router(intake_router)
    app.include_router(submissions_router)

    @app.get("/healthz", tags=["infra"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
