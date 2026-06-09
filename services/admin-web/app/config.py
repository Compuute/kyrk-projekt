"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    intake_base_url: str
    certificate_base_url: str
    membership_base_url: str
    cookie_name: str = "kyrk_session"
    cookie_secure: bool = False  # True in production behind HTTPS
    zitadel_issuer_url: str = ""
    zitadel_client_id: str = ""
    zitadel_client_secret: str = ""
    zitadel_redirect_uri: str = ""


def load_settings() -> Settings:
    return Settings(
        intake_base_url=os.getenv("INTAKE_BASE_URL", "http://localhost:8001"),
        certificate_base_url=os.getenv("CERTIFICATE_BASE_URL", "http://localhost:8002"),
        membership_base_url=os.getenv("MEMBERSHIP_BASE_URL", "http://localhost:8003"),
        cookie_name=os.getenv("ADMIN_WEB_COOKIE_NAME", "kyrk_session"),
        cookie_secure=os.getenv("ADMIN_WEB_COOKIE_SECURE", "false").lower() == "true",
        zitadel_issuer_url=os.getenv("ZITADEL_ISSUER_URL", ""),
        zitadel_client_id=os.getenv("ZITADEL_CLIENT_ID", ""),
        zitadel_client_secret=os.getenv("ZITADEL_CLIENT_SECRET", ""),
        zitadel_redirect_uri=os.getenv("ZITADEL_REDIRECT_URI", ""),
    )

