"""Adapter factory for admin-web.

ADAPTER_MODE=memory (default): fake clients + fake session (colon token).
ADAPTER_MODE=production: httpx clients + JWT session (PropelAuth RS256).

Required env vars in production mode:
- INTAKE_BASE_URL
- CERTIFICATE_BASE_URL
- REPORTING_BASE_URL          (activity endpoints are now served here too)
- PROPELAUTH_VERIFIER_KEY   RS256 public key PEM (from Secret Manager)
- PROPELAUTH_ISSUER          tenant issuer URL

NOTE: ACTIVITY_BASE_URL is no longer needed -- activity-service was merged
into reporting-service. The activity client now defaults to REPORTING_BASE_URL.
"""
from __future__ import annotations

import os
import sys

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
from app.ports.session import SessionPort
from app.ports.translation import TranslationPort


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_intake_client() -> IntakeClientPort:
    if _mode() == "production":
        from app.adapters.httpx_clients import HttpxIntakeClient

        return HttpxIntakeClient(base_url=_require_env("INTAKE_BASE_URL"))
    from app.adapters.fake_clients import FakeIntakeClient

    return FakeIntakeClient()


def make_certificate_client() -> CertificateClientPort:
    if _mode() == "production":
        from app.adapters.httpx_clients import HttpxCertificateClient

        return HttpxCertificateClient(base_url=_require_env("CERTIFICATE_BASE_URL"))
    from app.adapters.fake_clients import FakeCertificateClient

    return FakeCertificateClient()


def make_activity_client() -> ActivityClientPort:
    if _mode() == "production":
        from app.adapters.httpx_clients import HttpxActivityClient

        # activity-service was merged into reporting-service; activity
        # endpoints (/activities/*) are now served by REPORTING_BASE_URL.
        return HttpxActivityClient(base_url=_require_env("REPORTING_BASE_URL"))
    from app.adapters.fake_clients import FakeActivityClient

    return FakeActivityClient()


def make_reporting_client() -> ReportingClientPort:
    if _mode() == "production":
        from app.adapters.httpx_clients import HttpxReportingClient

        return HttpxReportingClient(base_url=_require_env("REPORTING_BASE_URL"))
    from app.adapters.fake_clients import FakeReportingClient

    return FakeReportingClient()


def make_notification() -> NotificationPort:
    if _mode() == "production":
        from app.adapters.webhook_notification import WebhookNotification

        return WebhookNotification()
    from app.adapters.fake_notification import FakeNotification

    return FakeNotification()


def make_funeral_tracker() -> FuneralTrackerPort:
    if _mode() == "production":
        from app.adapters.fake_funeral_tracker import FakeFuneralTracker

        return FakeFuneralTracker()
    from app.adapters.fake_funeral_tracker import FakeFuneralTracker

    return FakeFuneralTracker()


def make_grant_tracker() -> GrantTrackerPort:
    if _mode() == "production":
        # Firestore adapter would be imported here when available
        from app.adapters.fake_grant_tracker import FakeGrantTracker

        return FakeGrantTracker()
    from app.adapters.fake_grant_tracker import FakeGrantTracker

    return FakeGrantTracker()


def make_content_store() -> ContentStorePort:
    if _mode() == "production":
        # Cloud Storage adapter would be imported here when available
        from app.adapters.fake_content_store import FakeContentStore

        return FakeContentStore()
    from app.adapters.fake_content_store import FakeContentStore

    return FakeContentStore()


def make_translator() -> TranslationPort:
    if _mode() == "production":
        from app.adapters.anthropic_translator import AnthropicTranslator

        return AnthropicTranslator(api_key=_require_env("ANTHROPIC_API_KEY"))
    from app.adapters.fake_translator import FakeTranslator

    return FakeTranslator()


def make_session_adapter() -> SessionPort:
    if _mode() == "production":
        from app.adapters.jwt_session import JWTSessionAdapter

        key = _require_env("PROPELAUTH_VERIFIER_KEY")
        issuer = _require_env("PROPELAUTH_ISSUER")
        return JWTSessionAdapter(verifier_key=key, issuer=issuer)
    from app.adapters.fake_session import FakeSessionAdapter

    return FakeSessionAdapter()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[admin-web] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
