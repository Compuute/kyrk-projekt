from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_reports import router as reports_router


def create_app() -> FastAPI:
    app = FastAPI(title="reporting-service", version="0.1.0")
    app.include_router(reports_router)

    @app.get("/healthz", tags=["infra"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
