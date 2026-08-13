"""Adapter factory for membership-intake.

ADAPTER_MODE=memory (default):
  InMemorySubmissionRepository, InMemoryNotifier, InMemoryRateLimiter,
  FakeAuthAdapter, FakeMembershipClient.

ADAPTER_MODE=production:
  FirestoreSubmissionRepository, HttpNotifier, FirestoreRateLimiter,
  ZitadelAuthAdapter, HttpxMembershipClient.

Note on rate limiting: the production limiter shares one fixed window per
key across all Cloud Run instances via the `rate_limit_windows` Firestore
collection (the in-memory limiter is per instance and only for dev/test).

Required env vars in production mode:
- ZITADEL_ISSUER_URL
- ZITADEL_CLIENT_ID
- MEMBERSHIP_SERVICE_URL
- BREVO_API_KEY (donation receipts)
- RECEIPT_FROM_EMAIL (donation receipts)

Optional env vars:
- ADMIN_NOTIFY_WEBHOOK — admin push notification. If unset, notifications
  are disabled (no-op); intake submissions still work and are visible in
  admin-web. Never required for the public intake flow to succeed.
"""
from __future__ import annotations

import os
import sys

from app.ports.auth import AuthPort
from app.ports.donation_repository import DonationRepository
from app.ports.email_sender import EmailSenderPort
from app.ports.membership_client import MembershipClientPort
from app.ports.notifier import NotifierPort
from app.ports.rate_limiter import RateLimiterPort
from app.ports.submission_repository import SubmissionRepository


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_submission_repository() -> SubmissionRepository:
    if _mode() == "production":
        from app.adapters.firestore_submission_repository import (
            FirestoreSubmissionRepository,
        )

        return FirestoreSubmissionRepository()
    from app.adapters.in_memory_submission_repository import InMemorySubmissionRepository

    return InMemorySubmissionRepository()


def make_notifier() -> NotifierPort:
    if _mode() == "production":
        # ADMIN_NOTIFY_WEBHOOK is OPTIONAL. It is a non-critical push channel —
        # a missing/empty webhook must never block a member's intake submission
        # (admins still see pending intake in admin-web). If unset, no-op.
        url = os.getenv("ADMIN_NOTIFY_WEBHOOK", "")
        if url:
            from app.adapters.http_notifier import HttpNotifier

            return HttpNotifier(webhook_url=url)
        from app.adapters.noop_notifier import NoopNotifier

        return NoopNotifier()
    from app.adapters.in_memory_notifier import InMemoryNotifier

    return InMemoryNotifier()


def make_rate_limiter() -> RateLimiterPort:
    if _mode() == "production":
        from app.adapters.firestore_rate_limiter import FirestoreRateLimiter

        return FirestoreRateLimiter(max_hits=5, window_seconds=60)
    from app.adapters.in_memory_rate_limiter import InMemoryRateLimiter

    return InMemoryRateLimiter(max_hits=5, window_seconds=60)


def make_auth() -> AuthPort:
    if _mode() == "production":
        from app.adapters.zitadel_auth import ZitadelAuthAdapter

        issuer = _require_env("ZITADEL_ISSUER_URL")
        client_id = _require_env("ZITADEL_CLIENT_ID")
        return ZitadelAuthAdapter(issuer_url=issuer, client_id=client_id)
    from app.adapters.fake_auth import FakeAuthAdapter

    return FakeAuthAdapter()


def make_membership_client() -> MembershipClientPort:
    if _mode() == "production":
        from app.adapters.gcp_identity import metadata_id_token_provider
        from app.adapters.httpx_membership_client import HttpxMembershipClient

        url = _require_env("MEMBERSHIP_SERVICE_URL")
        return HttpxMembershipClient(
            base_url=url, id_token_provider=metadata_id_token_provider
        )
    from app.adapters.fake_membership_client import FakeMembershipClient

    return FakeMembershipClient()


def make_donation_repository() -> DonationRepository:
    if _mode() == "production":
        from app.adapters.firestore_donation_repository import (
            FirestoreDonationRepository,
        )

        return FirestoreDonationRepository()
    from app.adapters.in_memory_donation_repository import InMemoryDonationRepository

    return InMemoryDonationRepository()


def make_email_sender() -> EmailSenderPort:
    if _mode() == "production":
        from app.adapters.brevo_email_sender import BrevoEmailSender

        return BrevoEmailSender(
            api_key=_require_env("BREVO_API_KEY"),
            from_email=_require_env("RECEIPT_FROM_EMAIL"),
            from_name=os.getenv("RECEIPT_FROM_NAME", "Kyrkan"),
        )
    from app.adapters.fake_email_sender import FakeEmailSender

    return FakeEmailSender()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[membership-intake] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
