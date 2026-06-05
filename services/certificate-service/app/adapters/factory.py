"""Adapter factory for certificate-service.

ADAPTER_MODE=memory (default): in-memory repo/audit + fake auth.
ADAPTER_MODE=production: Firestore repo/audit + PropelAuth.

Required env vars in production mode:
- PROPELAUTH_URL
- PROPELAUTH_API_KEY

IAM notes: the service account needs
- roles/datastore.user on Firestore (security rules enforce per-collection)
- roles/secretmanager.secretAccessor on propelauth-api-key
That's it.
"""
from __future__ import annotations

import os
import sys

from app.ports.audit import AuditPort
from app.ports.auth import AuthPort
from app.ports.certificate_repository import CertificateRepository
from app.ports.pdf_generator import PdfGeneratorPort


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_certificate_repository() -> CertificateRepository:
    if _mode() == "production":
        from app.adapters.firestore_certificate_repository import (
            FirestoreCertificateRepository,
        )

        return FirestoreCertificateRepository()
    from app.adapters.in_memory_certificate_repository import InMemoryCertificateRepository

    return InMemoryCertificateRepository()


def make_audit() -> AuditPort:
    if _mode() == "production":
        from app.adapters.firestore_audit import FirestoreAuditAdapter

        return FirestoreAuditAdapter()
    from app.adapters.in_memory_audit import InMemoryAuditAdapter

    return InMemoryAuditAdapter()


def make_pdf_generator() -> PdfGeneratorPort:
    if _mode() == "production":
        from app.adapters.html_pdf_generator import HtmlPdfGenerator

        return HtmlPdfGenerator()
    from app.adapters.stub_pdf_generator import StubPdfGenerator

    return StubPdfGenerator()


def make_auth() -> AuthPort:
    if _mode() == "production":
        from app.adapters.propelauth_auth import PropelAuthAdapter

        url = _require_env("PROPELAUTH_URL")
        key = _require_env("PROPELAUTH_API_KEY")
        return PropelAuthAdapter(auth_url=url, api_key=key)
    from app.adapters.fake_auth import FakeAuthAdapter

    return FakeAuthAdapter()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[certificate-service] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
