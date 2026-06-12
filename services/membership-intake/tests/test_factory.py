import pytest

from app.adapters.factory import (
    make_auth,
    make_membership_client,
    make_notifier,
    make_rate_limiter,
    make_submission_repository,
)
from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.fake_membership_client import FakeMembershipClient
from app.adapters.in_memory_notifier import InMemoryNotifier
from app.adapters.in_memory_rate_limiter import InMemoryRateLimiter
from app.adapters.in_memory_submission_repository import InMemorySubmissionRepository


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in (
        "ADAPTER_MODE",
        "ZITADEL_ISSUER_URL",
        "ZITADEL_CLIENT_ID",
        "MEMBERSHIP_SERVICE_URL",
        "ADMIN_NOTIFY_WEBHOOK",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_submission_repository(), InMemorySubmissionRepository)
    assert isinstance(make_notifier(), InMemoryNotifier)
    assert isinstance(make_auth(), FakeAuthAdapter)
    assert isinstance(make_membership_client(), FakeMembershipClient)
    assert isinstance(make_rate_limiter(), InMemoryRateLimiter)


def test_production_rate_limiter_is_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    limiter = make_rate_limiter()
    assert type(limiter).__name__ == "FirestoreRateLimiter"


def test_production_repository_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    repo = make_submission_repository()
    assert type(repo).__name__ == "FirestoreSubmissionRepository"


def test_production_notifier_requires_webhook(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="ADMIN_NOTIFY_WEBHOOK"):
        make_notifier()

    monkeypatch.setenv("ADMIN_NOTIFY_WEBHOOK", "https://webhook.example/notify")
    notifier = make_notifier()
    assert type(notifier).__name__ == "HttpNotifier"


def test_production_auth_requires_zitadel_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="ZITADEL_ISSUER_URL"):
        make_auth()
    monkeypatch.setenv("ZITADEL_ISSUER_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="ZITADEL_CLIENT_ID"):
        make_auth()


def test_production_membership_client_requires_base_url(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="MEMBERSHIP_SERVICE_URL"):
        make_membership_client()
    monkeypatch.setenv("MEMBERSHIP_SERVICE_URL", "https://ms.example")
    client = make_membership_client()
    assert type(client).__name__ == "HttpxMembershipClient"
