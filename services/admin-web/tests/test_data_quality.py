"""Tests for data quality dashboard and compute_quality."""
from app.ports.data_quality import compute_quality, validate_email, validate_personnummer, validate_phone


class TestValidators:
    def test_valid_personnummer(self):
        assert validate_personnummer("19800101-1231") is True

    def test_invalid_personnummer(self):
        assert validate_personnummer("19800101-1234") is False

    def test_valid_phone(self):
        assert validate_phone("+46701234567") is True
        assert validate_phone("0701234567") is True

    def test_invalid_phone(self):
        assert validate_phone("12345") is False

    def test_valid_email(self):
        assert validate_email("test@example.com") is True

    def test_invalid_email(self):
        assert validate_email("not-email") is False


class TestComputeQuality:
    def test_empty_list(self):
        report = compute_quality([])
        assert report.total_members == 0
        assert report.completeness_pct == 0

    def test_perfect_data(self):
        members = [
            {"first_name": "Anna", "last_name": "A", "phone": "+46701234567",
             "email": "a@a.se", "personal_number": "19800101-1231"},
        ]
        report = compute_quality(members)
        assert report.total_members == 1
        assert report.completeness_pct == 100
        assert report.personnummer_pct == 100
        assert report.phone_pct == 100
        assert report.email_pct == 100
        assert report.duplicates == 0

    def test_missing_fields(self):
        members = [
            {"first_name": "Anna", "last_name": "A", "phone": "", "email": "", "personal_number": ""},
        ]
        report = compute_quality(members)
        assert report.completeness_pct == 0
        assert "phone" in report.missing_fields
        assert "email" in report.missing_fields

    def test_duplicates_detected(self):
        members = [
            {"first_name": "A", "last_name": "A", "phone": "0701", "email": "a@a.se", "personal_number": "19800101-1231"},
            {"first_name": "B", "last_name": "B", "phone": "0702", "email": "b@b.se", "personal_number": "19800101-1231"},
        ]
        report = compute_quality(members)
        assert report.duplicates == 1
        assert report.duplicate_pct > 0

    def test_no_duplicates(self):
        members = [
            {"first_name": "A", "last_name": "A", "phone": "0701234567", "email": "a@a.se", "personal_number": "19800101-1231"},
            {"first_name": "B", "last_name": "B", "phone": "0701234568", "email": "b@b.se", "personal_number": "19810101-1230"},
        ]
        report = compute_quality(members)
        assert report.duplicates == 0

    def test_invalid_personnummer_counted(self):
        members = [
            {"first_name": "A", "last_name": "A", "phone": "0701234567", "email": "a@a.se", "personal_number": "12345"},
        ]
        report = compute_quality(members)
        assert report.personnummer_pct == 0

    def test_redacted_fields_treated_as_missing(self):
        members = [
            {"first_name": "A", "last_name": "A", "phone": "***redacted***", "email": "***redacted***", "personal_number": "***redacted***"},
        ]
        report = compute_quality(members)
        assert report.completeness_pct == 0


class TestDataQualityRoute:
    def test_dashboard_requires_auth(self, client):
        resp = client.get("/data-quality")
        assert resp.status_code == 302

    def test_dashboard_renders(self, authed_client):
        resp = authed_client.get("/data-quality")
        assert resp.status_code == 200
        assert "Datakvalitet" in resp.text
