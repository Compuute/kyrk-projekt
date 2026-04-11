"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    intake_base_url: str
    certificate_base_url: str
    cookie_name: str = "kyrk_session"
    cookie_secure: bool = False  # True in production behind HTTPS


def load_settings() -> Settings:
    return Settings(
        intake_base_url=os.getenv("INTAKE_BASE_URL", "http://localhost:8001"),
        certificate_base_url=os.getenv("CERTIFICATE_BASE_URL", "http://localhost:8002"),
        cookie_name=os.getenv("ADMIN_WEB_COOKIE_NAME", "kyrk_session"),
        cookie_secure=os.getenv("ADMIN_WEB_COOKIE_SECURE", "false").lower() == "true",
    )
