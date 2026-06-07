from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.adapters.factory import (
    make_activity_client,
    make_certificate_client,
    make_content_store,
    make_funeral_tracker,
    make_grant_tracker,
    make_intake_client,
    make_notification,
    make_reporting_client,
    make_session_adapter,
    make_translator,
)
from app.config import Settings, load_settings
from app.ports.clients import (
    ActivityClientPort,
    CertificateClientPort,
    IntakeClientPort,
    ReportingClientPort,
)
from app.ports.content_store import ContentStorePort
from app.ports.funeral_tracker import FuneralTrackerPort
from app.ports.grant_tracker import GrantTrackerPort
from app.ports.notification import NotificationPort
from app.ports.session import SessionInfo, SessionPort
from app.ports.translation import TranslationPort


_INTAKE: IntakeClientPort | None = None
_CERTIFICATE: CertificateClientPort | None = None
_ACTIVITY: ActivityClientPort | None = None
_REPORTING: ReportingClientPort | None = None
_NOTIFICATION: NotificationPort | None = None
_FUNERAL_TRACKER: FuneralTrackerPort | None = None
_GRANT_TRACKER: GrantTrackerPort | None = None
_CONTENT_STORE: ContentStorePort | None = None
_TRANSLATOR: TranslationPort | None = None
_SESSION: SessionPort | None = None
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


def get_activity_client() -> ActivityClientPort:
    global _ACTIVITY
    if _ACTIVITY is None:
        _ACTIVITY = make_activity_client()
    return _ACTIVITY


def get_reporting_client() -> ReportingClientPort:
    global _REPORTING
    if _REPORTING is None:
        _REPORTING = make_reporting_client()
    return _REPORTING


def get_notification() -> NotificationPort:
    global _NOTIFICATION
    if _NOTIFICATION is None:
        _NOTIFICATION = make_notification()
    return _NOTIFICATION


def get_funeral_tracker() -> FuneralTrackerPort:
    global _FUNERAL_TRACKER
    if _FUNERAL_TRACKER is None:
        _FUNERAL_TRACKER = make_funeral_tracker()
    return _FUNERAL_TRACKER


def get_grant_tracker() -> GrantTrackerPort:
    global _GRANT_TRACKER
    if _GRANT_TRACKER is None:
        _GRANT_TRACKER = make_grant_tracker()
    return _GRANT_TRACKER


def get_content_store() -> ContentStorePort:
    global _CONTENT_STORE
    if _CONTENT_STORE is None:
        _CONTENT_STORE = make_content_store()
    return _CONTENT_STORE


def get_translator() -> TranslationPort:
    global _TRANSLATOR
    if _TRANSLATOR is None:
        _TRANSLATOR = make_translator()
    return _TRANSLATOR


def get_session_adapter() -> SessionPort:
    global _SESSION
    if _SESSION is None:
        _SESSION = make_session_adapter()
    return _SESSION


def current_session(
    kyrk_session: str | None = Cookie(default=None),
    session_adapter: SessionPort = Depends(get_session_adapter),
) -> SessionInfo:
    info = session_adapter.validate(kyrk_session)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"Location": "/login"},
        )
    return info


def redirect_if_unauthenticated(
    kyrk_session: str | None = Cookie(default=None),
    session_adapter: SessionPort = Depends(get_session_adapter),
) -> SessionInfo | RedirectResponse:
    info = session_adapter.validate(kyrk_session)
    if info is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return info
