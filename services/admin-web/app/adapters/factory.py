"""Adapter factory for admin-web.

ADAPTER_MODE=memory (default): in-process fake clients with seedable
state. Used by tests, local dev, and the screenshot harness.

ADAPTER_MODE=production: HttpxIntakeClient + HttpxCertificateClient
pointing at real Cloud Run service URLs from env. The bearer token
forwarded to the downstream services is the user's session token —
admin-web never holds privileged credentials of its own.

Required env vars in production mode:
- INTAKE_BASE_URL          e.g. https://intake-xyz.a.run.app
- CERTIFICATE_BASE_URL     e.g. https://certificates-xyz.a.run.app
"""
from __future__ import annotations

import os
import sys

from app.ports.clients import CertificateClientPort, IntakeClientPort


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


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[admin-web] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
