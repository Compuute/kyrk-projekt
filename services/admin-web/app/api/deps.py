from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.adapters.fake_clients import FakeCertificateClient, FakeIntakeClient
from app.adapters.fake_session import SessionInfo, parse_session_cookie
from app.config import Settings, load_settings
from app.ports.clients import CertificateClientPort, IntakeClientPort


# Singleton in-memory clients for MVP / local dev / tests.
# Production wires the httpx adapters here (see config.py + README).
_INTAKE: IntakeClientPort = FakeIntakeClient()
_CERTIFICATE: CertificateClientPort = FakeCertificateClient()
_SETTINGS: Settings = load_settings()


def get_settings() -> Settings:
    return _SETTINGS


def get_intake_client() -> IntakeClientPort:
    return _INTAKE


def get_certificate_client() -> CertificateClientPort:
    return _CERTIFICATE


def current_session(
    kyrk_session: str | None = Cookie(default=None),
) -> SessionInfo:
    info = parse_session_cookie(kyrk_session)
    if info is None:
        # For full-page routes we prefer a redirect; callers that want 401
        # wrap this in a different dependency.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"Location": "/login"},
        )
    return info


def redirect_if_unauthenticated(
    kyrk_session: str | None = Cookie(default=None),
) -> SessionInfo | RedirectResponse:
    """Alternative to current_session that returns a RedirectResponse on miss.

    Used by GET page handlers so anonymous users see the login page instead
    of a raw 401.
    """
    info = parse_session_cookie(kyrk_session)
    if info is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return info
