"""Tests for input validation — personnummer, phone, name."""
from __future__ import annotations

import pytest

from app.api.routes_intake import IntakeRequest, _luhn_check, _normalize_phone


class TestLuhnCheck:
    def test_valid_personnummer(self):
        assert _luhn_check("8507099805") is True

    def test_invalid_personnummer(self):
        assert _luhn_check("8507099806") is False

    def test_all_zeros(self):
        assert _luhn_check("0000000000") is True

    def test_samordningsnummer(self):
        # dag + 60: 85 07 69 9805
        assert _luhn_check("8507699805") is False  # different check digit


class TestNormalizePhone:
    def test_07_format(self):
        assert _normalize_phone("0701234567") == "+46701234567"

    def test_plus46_format(self):
        assert _normalize_phone("+46701234567") == "+46701234567"

    def test_with_dashes(self):
        assert _normalize_phone("070-123 45 67") == "+46701234567"

    def test_with_spaces(self):
        assert _normalize_phone("070 123 45 67") == "+46701234567"


class TestIntakeRequestValidation:
    def _valid_payload(self, **overrides) -> dict:
        base = {
            "church_id": "c1",
            "first_name": "Anna",
            "last_name": "Andersson",
            "phone": "0701234567",
            "email": "anna@test.se",
            "personal_number": "19850709-9805",
            "gdpr_consent": True,
            "consent_timestamp": "2026-06-06T12:00:00Z",
        }
        base.update(overrides)
        return base

    def test_valid_request(self):
        req = IntakeRequest(**self._valid_payload())
        assert req.first_name == "Anna"
        assert req.phone == "+46701234567"

    def test_name_with_digits_rejected(self):
        with pytest.raises(Exception, match="siffror"):
            IntakeRequest(**self._valid_payload(first_name="Anna2"))

    def test_name_too_short_rejected(self):
        with pytest.raises(Exception):
            IntakeRequest(**self._valid_payload(first_name="A"))

    def test_name_with_amharic_accepted(self):
        req = IntakeRequest(**self._valid_payload(first_name="አበበ"))
        assert req.first_name == "አበበ"

    def test_name_with_swedish_chars_accepted(self):
        req = IntakeRequest(**self._valid_payload(first_name="Åsa", last_name="Öström"))
        assert req.first_name == "Åsa"

    def test_name_trimmed(self):
        req = IntakeRequest(**self._valid_payload(first_name="  Anna  "))
        assert req.first_name == "Anna"

    def test_phone_normalized_to_e164(self):
        req = IntakeRequest(**self._valid_payload(phone="070-123 45 67"))
        assert req.phone == "+46701234567"

    def test_phone_invalid_rejected(self):
        with pytest.raises(Exception, match="telefonnummer"):
            IntakeRequest(**self._valid_payload(phone="12345"))

    def test_phone_letters_rejected(self):
        with pytest.raises(Exception, match="telefonnummer"):
            IntakeRequest(**self._valid_payload(phone="abcdefghij"))

    def test_personnummer_valid(self):
        req = IntakeRequest(**self._valid_payload(personal_number="19850709-9805"))
        assert req.personal_number == "19850709-9805"

    def test_personnummer_invalid_checksum(self):
        with pytest.raises(Exception, match="kontrollsiffra"):
            IntakeRequest(**self._valid_payload(personal_number="19850709-9806"))

    def test_personnummer_short_format(self):
        req = IntakeRequest(**self._valid_payload(personal_number="850709-9805"))
        assert req.personal_number == "850709-9805"

    def test_personnummer_wrong_format(self):
        with pytest.raises(Exception, match="format"):
            IntakeRequest(**self._valid_payload(personal_number="123"))

    def test_email_invalid_rejected(self):
        with pytest.raises(Exception):
            IntakeRequest(**self._valid_payload(email="not-an-email"))

    def test_email_valid(self):
        req = IntakeRequest(**self._valid_payload(email="test@example.com"))
        assert req.email == "test@example.com"
