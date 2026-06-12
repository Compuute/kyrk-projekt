"""Adapter factory for agent-worker.

ADAPTER_MODE=memory (default):
  FakeReportingClient, InMemoryAuditLog.

ADAPTER_MODE=production:
  HttpxReportingClient (with Cloud Run service identity), FirestoreAuditLog.

Required env vars in production mode:
- REPORTING_SERVICE_URL
- AGENT_REPORTING_TOKEN — Zitadel machine-user token the agent acts as.
  Scope note: the token's org claim defines which church the reports are
  generated for; one token = one church scope (single shared org today,
  see docs/28 skuldpost 2).
"""
from __future__ import annotations

import os
import sys

from app.ports.audit_log import AuditLogPort
from app.ports.reporting_client import ReportingClientPort


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_reporting_client() -> ReportingClientPort:
    if _mode() == "production":
        from app.adapters.gcp_identity import metadata_id_token_provider
        from app.adapters.httpx_reporting_client import HttpxReportingClient

        return HttpxReportingClient(
            base_url=_require_env("REPORTING_SERVICE_URL"),
            token=_require_env("AGENT_REPORTING_TOKEN"),
            id_token_provider=metadata_id_token_provider,
        )
    from app.adapters.fake_reporting_client import FakeReportingClient

    return FakeReportingClient()


def make_audit_log() -> AuditLogPort:
    if _mode() == "production":
        from app.adapters.firestore_audit_log import FirestoreAuditLog

        return FirestoreAuditLog()
    from app.adapters.in_memory_audit_log import InMemoryAuditLog

    return InMemoryAuditLog()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[agent-worker] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
