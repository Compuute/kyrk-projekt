import pytest

from app.domain.errors import PIIRejected
from app.domain.pii_guard import assert_no_pii


def test_clean_payload_passes():
    assert_no_pii({"participants_total": 20, "age_band_counts": {"0-6": 5}})


def test_top_level_forbidden_rejected():
    with pytest.raises(PIIRejected):
        assert_no_pii({"first_name": "Anna"})


def test_nested_forbidden_rejected():
    with pytest.raises(PIIRejected):
        assert_no_pii({"activities": [{"participants_total": 1, "email": "x"}]})


def test_case_insensitive_match():
    with pytest.raises(PIIRejected):
        assert_no_pii({"FirstName": "Anna"})


def test_list_of_dicts_walked():
    with pytest.raises(PIIRejected):
        assert_no_pii([{"ok": 1}, {"personal_number": "x"}])


def test_primitives_are_ignored():
    assert_no_pii(42)
    assert_no_pii("just a string")
    assert_no_pii(None)
