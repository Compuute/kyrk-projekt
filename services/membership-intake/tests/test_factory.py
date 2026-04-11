import pytest

from app.adapters.factory import (
    make_auth,
    make_membership_client,
    make_notifier,
    make_submission_repository,
)
from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.fake_membership_client import FakeMembershipClient
from app.adapters.in_memory_notifier import InMemoryNotifier
from app.adapters.in_memory_submission_repository import InMemorySubmissionRepository


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in (
        "ADAPTER_MODE",
        "PROPELAUTH_URL",
        "PROPELAUTH_API_KEY",
        "MEMBERSHIP_SERVICE_URL",
        "ADMIN_NOTIFY_WEBHOOK",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_submission_repository(), InMemorySubmissionRepository)
    assert isinstance(make_notifier(), InMemoryNotifier)
    assert isinstance(make_auth(), FakeAuthAdapter)
    assert isinstance(make_membership_client(), FakeMembershipClient)


def test_production_repository_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    repo = make_submission_repository()
    assert type(repo).__name__ == "FirestoreSubmissionRepository"


def test_production_notifier_requires_webhook(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="ADMIN_NOTIFY_WEBHOOK"):
        make_notifier()

    monkeypatch.setenv("ADMIN_NOTIFY_WEBHOOK", "https://n8n.example/webhook")
    notifier = make_notifier()
    assert type(notifier).__name__ == "HttpNotifier"


def test_production_auth_requires_propelauth_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="PROPELAUTH_URL"):
        make_auth()
    monkeypatch.setenv("PROPELAUTH_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="PROPELAUTH_API_KEY"):
        make_auth()


def test_production_membership_client_requires_base_url(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="MEMBERSHIP_SERVICE_URL"):
        make_membership_client()
    monkeypatch.setenv("MEMBERSHIP_SERVICE_URL", "https://ms.example")
    client = make_membership_client()
    assert type(client).__name__ == "HttpxMembershipClient"
