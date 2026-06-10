from unittest.mock import MagicMock
import pytest
from app.adapters.firestore_submission_repository import FirestoreSubmissionRepository
from app.domain.models import IntakeSubmission, SubmissionStatus


def test_firestore_repo_find_by_personal_number():
    mock_client = MagicMock()
    repo = FirestoreSubmissionRepository(client=mock_client)

    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {
        "submission_id": "sub123",
        "church_id": "church123",
        "first_name": "Anna",
        "last_name": "Smoke",
        "phone": "+46701234567",
        "email": "anna@test.se",
        "personal_number": "19850709-9805",
        "gdpr_consent": True,
        "consent_timestamp": "2026-06-06T12:00:00Z",
        "status": "pending",
        "received_at": "2026-06-06T12:00:00Z",
    }

    mock_client.collection.return_value.where.return_value.stream.return_value = [mock_doc]

    res = repo.find_by_personal_number("19850709-9805")
    assert res is not None
    assert res.first_name == "Anna"
    assert res.personal_number == "19850709-9805"

    # Verify query structure
    mock_client.collection.assert_called_with("intake_submissions")
    mock_client.collection.return_value.where.assert_called_once()
    args, kwargs = mock_client.collection.return_value.where.call_args
    assert args[0] == "personal_number"
    assert args[1] == "in"
    assert "19850709-9805" in args[2]


def test_firestore_repo_find_by_personal_number_no_match():
    mock_client = MagicMock()
    repo = FirestoreSubmissionRepository(client=mock_client)

    mock_client.collection.return_value.where.return_value.stream.return_value = []

    res = repo.find_by_personal_number("19850709-9805")
    assert res is None
