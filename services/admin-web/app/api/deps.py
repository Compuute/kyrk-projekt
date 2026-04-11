from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.adapters.factory import make_certificate_client, make_intake_client
from app.adapters.fake_session import SessionInfo, parse_session_cookie
from app.config import Settings, load_settings
from app.ports.clients import CertificateClientPort, IntakeClientPort


_INTAKE: IntakeClientPort | None = None
_CERTIFICATE: CertificateClientPort | None = None
_SETTINGS: Settings = load_settings()


def get_settings() -> Settings:
    return _SETTINGS


def get_intake_client() -> IntakeClientPort:
    global _INTAKE
    if _INTAKE is None:
        _INTAKE = make_intake_client()
    return _INTAKE


def get_certificate_client() -> CertificateClientPort:
    global _CERTIFICATE
    if _CERTIFICATE is None:
        _CERTIFICATE = make_certificate_client()
    return _CERTIFICATE


def current_session(
    kyrk_session: str | None = Cookie(default=None),
) -> SessionInfo:
    info = parse_session_cookie(kyrk_session)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"Location": "/login"},
        )
    return info


def redirect_if_unauthenticated(
    kyrk_session: str | None = Cookie(default=None),
) -> SessionInfo | RedirectResponse:
    """Alternative to current_session that returns a RedirectResponse on miss."""
    info = parse_session_cookie(kyrk_session)
    if info is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return info
