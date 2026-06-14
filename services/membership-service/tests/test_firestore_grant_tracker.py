"""Tests for FirestoreGrantTracker adapter."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.adapters.firestore_grant_tracker import FirestoreGrantTracker
from app.domain.models import GrantApplication


class MockDocSnap:
    def __init__(self, exists: bool, data: dict = None):
        self.exists = exists
        self._data = data or {}

    def to_dict(self):
        return self._data


def test_firestore_grant_tracker_save_and_get():
    mock_client = MagicMock()
    tracker = FirestoreGrantTracker(client=mock_client)

    app = GrantApplication(
        grant_id="grant1",
        church_id="c1",
        status="in_progress",
        started_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc),
        submitted_at=None,
        amount_requested=5000.0,
        amount_granted=None,
        notes="Some notes",
        generated_draft_url="https://draft.example",
        project_name="Youth Activity",
        project_description="Desc",
        target_group="Youth",
        budget_amount=6000.0,
        own_contribution=1000.0,
    )

    tracker.save_application(app)
    mock_client.collection.assert_called_once_with("grants")
    mock_client.collection().document.assert_called_with("c1__grant1")
    mock_client.collection().document().set.assert_called_once()
    saved_data = mock_client.collection().document().set.call_args[0][0]
    assert saved_data["grant_id"] == "grant1"
    assert saved_data["church_id"] == "c1"
    assert saved_data["project_name"] == "Youth Activity"
    assert saved_data["started_at"] == "2026-06-09T12:00:00+00:00"
    assert saved_data["submitted_at"] is None

    mock_client.reset_mock()
    mock_doc = MockDocSnap(exists=True, data=saved_data)
    mock_client.collection().document().get.return_value = mock_doc

    retrieved = tracker.get_application("c1", "grant1")
    assert retrieved is not None
    assert retrieved.grant_id == "grant1"
    assert retrieved.project_name == "Youth Activity"
    assert retrieved.started_at == app.started_at

    mock_client.reset_mock()
    mock_client.collection().document().get.return_value = MockDocSnap(exists=False)
    assert tracker.get_application("c1", "grant2") is None


def test_firestore_grant_tracker_list():
    mock_client = MagicMock()
    tracker = FirestoreGrantTracker(client=mock_client)

    mock_doc1 = MockDocSnap(exists=True, data={"grant_id": "grant1", "church_id": "c1", "project_name": "Proj1"})
    mock_doc2 = MockDocSnap(exists=True, data={"grant_id": "grant2", "church_id": "c1", "project_name": "Proj2"})

    mock_query = MagicMock()
    mock_query.stream.return_value = [mock_doc1, mock_doc2]
    mock_client.collection().where.return_value = mock_query

    apps = tracker.list_applications("c1")
    assert len(apps) == 2
    assert apps[0].grant_id == "grant1"
    assert apps[1].grant_id == "grant2"
    mock_client.collection().where.assert_called_once_with("church_id", "==", "c1")


def test_firestore_grant_tracker_lazy_client(monkeypatch):
    mock_client_class = MagicMock()
    import google.cloud.firestore

    monkeypatch.setattr(google.cloud.firestore, "Client", mock_client_class)

    tracker = FirestoreGrantTracker()
    tracker._coll()
    mock_client_class.assert_called_once()
