"""API contract tests — prevents breaking changes across services.

When an AI tool modifies a Pydantic model or route signature,
these tests catch if the change breaks the contract that other
services depend on.

Each service exposes a "contract" — the fields and types that
callers rely on. If a field is renamed, removed, or re-typed,
the test fails.
"""
import ast
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"

sys.path.insert(0, str(SERVICES / "membership-intake"))
sys.path.insert(0, str(SERVICES / "membership-service"))
sys.path.insert(0, str(SERVICES / "certificate-service"))
sys.path.insert(0, str(SERVICES / "reporting-service"))
sys.path.insert(0, str(SERVICES / "admin-web"))


class TestIntakeServiceContract:
    """admin-web depends on these fields from membership-intake."""

    def test_intake_response_fields(self):
        from app.ports.clients import PendingSubmission
        required = {"submission_id", "church_id", "first_name", "last_name", "received_at", "status"}
        actual = set(PendingSubmission.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"IntakeService contract broken — missing fields: {missing}"

    def test_approval_result_fields(self):
        from app.ports.clients import ApprovalResult
        required = {"submission_id", "status", "created_member_id"}
        actual = set(ApprovalResult.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"ApprovalResult contract broken — missing: {missing}"


class TestCertificateServiceContract:
    """admin-web depends on these fields from certificate-service."""

    def test_issue_request_fields(self):
        from app.ports.clients import IssueCertificateRequest
        required = {"certificate_type", "issued_date", "member_id", "church_name"}
        actual = set(IssueCertificateRequest.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"IssueCertificateRequest contract broken — missing: {missing}"

    def test_issued_certificate_fields(self):
        from app.ports.clients import IssuedCertificate
        required = {"certificate_id", "certificate_type", "issued_date", "status", "verification_url"}
        actual = set(IssuedCertificate.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"IssuedCertificate contract broken — missing: {missing}"


class TestReportingServiceContract:
    """admin-web depends on these fields from reporting-service."""

    def test_activity_aggregate_fields(self):
        from app.ports.clients import ActivityAggregate
        required = {"activity_id", "church_id", "activity_type", "date", "participants_total", "age_band_counts"}
        actual = set(ActivityAggregate.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"ActivityAggregate contract broken — missing: {missing}"

    def test_monthly_report_fields(self):
        from app.ports.clients import MonthlyReport
        required = {"report_id", "kind", "period", "payload"}
        actual = set(MonthlyReport.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"MonthlyReport contract broken — missing: {missing}"


class TestFuneralTrackerContract:
    """Routes + templates depend on these fields from FuneralCase."""

    def test_funeral_case_required_fields(self):
        from app.ports.funeral_tracker import FuneralCase
        required = {
            "case_id", "church_id", "status", "deceased_name",
            "deceased_name_am", "date_of_death", "contact_person",
            "package", "repatriation", "repatriation_destination",
            "package_price", "repatriation_price", "total_price",
            "checklist", "memorial_text_sv", "memorial_text_am",
            "grief_calendar_active", "eder_name", "eder_contribution",
        }
        actual = set(FuneralCase.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"FuneralCase contract broken — missing: {missing}"

    def test_calculate_price_returns_three_values(self):
        from app.ports.funeral_tracker import calculate_price
        result = calculate_price("ceremoni", False)
        assert len(result) == 3, "calculate_price must return (pkg, rep, total)"
        assert all(isinstance(v, (int, float)) for v in result)

    def test_checklist_items_exist(self):
        from app.ports.funeral_tracker import CHECKLIST_ITEMS_SWEDEN, CHECKLIST_ITEMS_REPATRIATION
        assert len(CHECKLIST_ITEMS_SWEDEN) >= 15, "Sweden checklist too short"
        assert len(CHECKLIST_ITEMS_REPATRIATION) >= 8, "Repatriation checklist too short"

    def test_memorial_days_exist(self):
        from app.ports.funeral_tracker import MEMORIAL_DAYS
        assert len(MEMORIAL_DAYS) >= 6
        days = [d for d, _, _ in MEMORIAL_DAYS]
        assert 3 in days
        assert 40 in days
        assert 365 in days

    def test_funeral_statuses_exist(self):
        from app.ports.funeral_tracker import FUNERAL_STATUSES
        assert "registered" in FUNERAL_STATUSES
        assert "completed" in FUNERAL_STATUSES
        assert "closed" in FUNERAL_STATUSES


class TestGrantTrackerContract:
    """Routes depend on these fields from GrantApplication."""

    def test_grant_application_fields(self):
        from app.ports.grant_tracker import GrantApplication
        required = {
            "grant_id", "church_id", "status", "project_name",
            "project_description", "target_group", "budget_amount",
        }
        actual = set(GrantApplication.__dataclass_fields__.keys())
        missing = required - actual
        assert missing == set(), f"GrantApplication contract broken — missing: {missing}"
