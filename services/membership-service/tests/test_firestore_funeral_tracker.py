"""Tests for FirestoreFuneralTracker adapter."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.adapters.firestore_funeral_tracker import FirestoreFuneralTracker
from app.domain.models import FuneralCase


class MockDocSnap:
    def __init__(self, exists: bool, data: dict = None):
        self.exists = exists
        self._data = data or {}

    def to_dict(self):
        return self._data


def test_firestore_funeral_tracker_save_and_get():
    mock_client = MagicMock()
    tracker = FirestoreFuneralTracker(client=mock_client)

    case = FuneralCase(
        case_id="case1",
        church_id="c1",
        status="registered",
        created_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc),
        deceased_name="John Doe",
        contact_person="Jane Doe",
        contact_phone="+4670000001",
    )

    # Test save
    tracker.save_case(case)
    mock_client.collection.assert_called_once_with("funerals")
    mock_client.collection().document.assert_called_with("c1__case1")
    mock_client.collection().document().set.assert_called_once()
    saved_data = mock_client.collection().document().set.call_args[0][0]
    assert saved_data["case_id"] == "case1"
    assert saved_data["church_id"] == "c1"
    assert saved_data["deceased_name"] == "John Doe"
    assert saved_data["created_at"] == "2026-06-09T12:00:00+00:00"

    # Test get - existing
    mock_client.reset_mock()
    mock_doc = MockDocSnap(exists=True, data=saved_data)
    mock_client.collection().document().get.return_value = mock_doc

    retrieved = tracker.get_case("c1", "case1")
    assert retrieved is not None
    assert retrieved.case_id == "case1"
    assert retrieved.deceased_name == "John Doe"
    assert retrieved.created_at == case.created_at
    mock_client.collection().document.assert_called_with("c1__case1")
    mock_client.collection().document().get.assert_called_once()

    # Test get - non-existent
    mock_client.reset_mock()
    mock_doc_missing = MockDocSnap(exists=False)
    mock_client.collection().document().get.return_value = mock_doc_missing
    retrieved_missing = tracker.get_case("c1", "case2")
    assert retrieved_missing is None


def test_firestore_funeral_tracker_list_and_delete():
    mock_client = MagicMock()
    tracker = FirestoreFuneralTracker(client=mock_client)

    # Test list_cases
    mock_doc1 = MockDocSnap(exists=True, data={"case_id": "case1", "church_id": "c1", "deceased_name": "John Doe"})
    mock_doc2 = MockDocSnap(exists=True, data={"case_id": "case2", "church_id": "c1", "deceased_name": "Jane Doe"})

    mock_query = MagicMock()
    mock_query.stream.return_value = [mock_doc1, mock_doc2]
    mock_client.collection().where.return_value = mock_query

    cases = tracker.list_cases("c1")
    assert len(cases) == 2
    assert cases[0].case_id == "case1"
    assert cases[1].case_id == "case2"
    mock_client.collection().where.assert_called_once_with("church_id", "==", "c1")
    mock_query.stream.assert_called_once()

    # Test delete_case
    mock_client.reset_mock()
    tracker.delete_case("c1", "case1")
    mock_client.collection().document.assert_called_once_with("c1__case1")
    mock_client.collection().document().delete.assert_called_once()


def test_firestore_funeral_tracker_lazy_client(monkeypatch):
    mock_client_class = MagicMock()
    import google.cloud.firestore

    monkeypatch.setattr(google.cloud.firestore, "Client", mock_client_class)

    tracker = FirestoreFuneralTracker()
    tracker._coll()
    mock_client_class.assert_called_once()
