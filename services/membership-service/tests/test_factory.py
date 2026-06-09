"""Factory-selection tests.

These verify that `make_*` picks the right adapter class based on
ADAPTER_MODE WITHOUT importing or instantiating the production
adapters' heavy dependencies. We only check identity of the returned
class, not any live call.
"""
import os

import pytest

from app.adapters.factory import (
    make_audit,
    make_auth,
    make_encryption,
    make_member_repository,
    make_funeral_tracker,
)
from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_encryption import InMemoryEncryptionAdapter
from app.adapters.in_memory_member_repository import InMemoryMemberRepository


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ADAPTER_MODE", raising=False)
    monkeypatch.delenv("KMS_KEY_NAME", raising=False)
    monkeypatch.delenv("ZITADEL_ISSUER_URL", raising=False)
    monkeypatch.delenv("ZITADEL_CLIENT_ID", raising=False)


def test_default_mode_is_memory():
    from app.adapters.in_memory_funeral_tracker import InMemoryFuneralTracker
    assert isinstance(make_member_repository(), InMemoryMemberRepository)
    assert isinstance(make_audit(), InMemoryAuditAdapter)
    assert isinstance(make_encryption(), InMemoryEncryptionAdapter)
    assert isinstance(make_auth(), FakeAuthAdapter)
    assert isinstance(make_funeral_tracker(), InMemoryFuneralTracker)


def test_explicit_memory_mode(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "memory")
    assert isinstance(make_member_repository(), InMemoryMemberRepository)


def test_production_encryption_requires_key_name(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="KMS_KEY_NAME"):
        make_encryption()


def test_production_auth_requires_zitadel_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="ZITADEL_ISSUER_URL"):
        make_auth()

    monkeypatch.setenv("ZITADEL_ISSUER_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="ZITADEL_CLIENT_ID"):
        make_auth()


def test_production_member_repository_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    # The factory should return a FirestoreMemberRepository instance WITHOUT
    # instantiating a live Firestore client (the client is lazy).
    repo = make_member_repository()
    assert type(repo).__name__ == "FirestoreMemberRepository"


def test_production_audit_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    audit = make_audit()
    assert type(audit).__name__ == "FirestoreAuditAdapter"


def test_production_funeral_tracker_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    tracker = make_funeral_tracker()
    assert type(tracker).__name__ == "FirestoreFuneralTracker"
