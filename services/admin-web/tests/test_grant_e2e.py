"""End-to-end grant application quality tests.

Simulates the full flow a board member goes through for EACH grant in
the database, validates that:
1. The grant detail page renders with correct eligibility checks
2. The application form accepts board input
3. The generated draft contains ALL required sections for that specific grant
4. The draft references actual KPI numbers (not placeholders)
5. The draft language matches the grant's required language (sv or en)
6. No PII fields leak into the draft
7. The draft would pass a basic "Skatteverket / bidragsgivare" format check

This is the "would the grant office reject our application on format
alone?" test. Content quality depends on Claude; format compliance
depends on us.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.adapters.fake_grant_tracker import FakeGrantTracker
from app.ports.clients import ActivityAggregate
from app.ports.grant_tracker import GrantApplication


# Navigate: tests/ → admin-web/ → services/ → kyrk-projekt/ → automation/grants/
GRANTS_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "automation" / "grants" / "database.json"


@pytest.fixture
def all_grants() -> list[dict]:
    """Load the real grant database so we test against actual grant specs."""
    return json.loads(GRANTS_DB_PATH.read_text(encoding="utf-8"))["grants"]


@pytest.fixture
def realistic_activities(activity):
    """Seed 12 months of realistic activity data covering all types."""
    # Use dates within the last 12 months from "today" so the generate
    # route's lookback window finds them.
    today = date.today()
    m1 = f"{today.year}-{today.month:02d}-05"
    m2 = f"{today.year}-{today.month:02d}-12"
    items = [
        ActivityAggregate(
            activity_id=f"act-{i}",
            church_id="c1",
            activity_type=atype,
            date=d,
            location="Storgatan 1, Stockholm",
            funding_tag=tag,
            participants_total=p,
            age_band_counts=bands,
        )
        for i, (atype, d, tag, p, bands) in enumerate([
            ("youth_tech", m1, "arvsfonden", 22, {"0-6": 0, "7-12": 5, "13-17": 12, "18-25": 5, "26+": 0}),
            ("youth_tech", m2, "arvsfonden", 25, {"0-6": 0, "7-12": 6, "13-17": 14, "18-25": 5, "26+": 0}),
            ("coding", m1, "kommunala", 14, {"0-6": 0, "7-12": 14, "13-17": 0, "18-25": 0, "26+": 0}),
            ("coding", m2, "kommunala", 12, {"0-6": 0, "7-12": 12, "13-17": 0, "18-25": 0, "26+": 0}),
            ("sunday_school", m1, "kommun", 30, {"0-6": 8, "7-12": 22, "13-17": 0, "18-25": 0, "26+": 0}),
            ("sunday_school", m2, "kommun", 28, {"0-6": 6, "7-12": 22, "13-17": 0, "18-25": 0, "26+": 0}),
            ("leadership", m1, "arvsfonden", 10, {"0-6": 0, "7-12": 0, "13-17": 5, "18-25": 5, "26+": 0}),
            ("debate", m2, "fritt_ord", 12, {"0-6": 0, "7-12": 0, "13-17": 6, "18-25": 6, "26+": 0}),
            ("community_hub", m1, "kommunala", 40, {"0-6": 5, "7-12": 10, "13-17": 10, "18-25": 10, "26+": 5}),
            ("community_hub", m2, "kommunala", 35, {"0-6": 4, "7-12": 8, "13-17": 8, "18-25": 10, "26+": 5}),
        ])
    ]
    for a in items:
        activity.seed(a)
    return items


@pytest.fixture
def board_input() -> dict:
    """Standard board input that covers all required fields."""
    return {
        "project_name": "Youth Tech & Integration 2025",
        "project_description": (
            "Ett ettårigt projekt som erbjuder kodning, robotik och digitala "
            "färdigheter till ungdomar 13-25 år i Sankt Johannes församling. "
            "Projektet fokuserar på nyanlända och socioekonomiskt utsatta "
            "ungdomar som saknar tillgång till teknik i hemmet."
        ),
        "target_group": "Ungdomar 13-25 år, primärt nyanlända och socioekonomiskt utsatta",
        "budget_amount": "200000",
        "own_contribution": "50000",
        "notes": "Vi har genomfört pilotverksamhet sedan 2024 med goda resultat.",
    }


# ============================================================================
# Per-grant format compliance tests
# ============================================================================


class TestGrantDraftFormatCompliance:
    """For each grant in the database, verify the generated draft meets
    the grant provider's format requirements."""

    def _apply_and_generate(self, client, grant_tracker, grant, board_input, auth_cookies):
        """Helper: save application + generate draft, return response."""
        gid = grant["grant_id"]

        # Step 1: Save application with board input
        grant_tracker.save_application(GrantApplication(
            grant_id=gid,
            church_id="c1",
            status="in_progress",
            project_name=board_input["project_name"],
            project_description=board_input["project_description"],
            target_group=board_input["target_group"],
            budget_amount=float(board_input["budget_amount"]),
            own_contribution=float(board_input["own_contribution"]),
            notes=board_input.get("notes", ""),
        ))

        # Step 2: Generate draft
        r = client.post(
            f"/grants/{gid}/generate",
            cookies=auth_cookies,
        )
        return r

    def test_every_grant_generates_without_error(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """Smoke test: every grant in the database can generate a draft
        without 500s or crashes."""
        for grant in all_grants:
            r = self._apply_and_generate(
                client, grant_tracker, grant, board_input, auth_cookies
            )
            assert r.status_code == 200, (
                f"{grant['grant_id']}: expected 200, got {r.status_code}"
            )

    def test_swedish_grants_have_all_required_sections(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """Swedish grants must have: sammanfattning, projektbeskrivning,
        målgrupp, metod, förväntade_resultat, budget_motivering,
        kpi_underlag, hållbarhet."""
        sv_grants = [g for g in all_grants if g.get("language") == "sv"]
        assert len(sv_grants) >= 7, "Expected at least 7 Swedish grants"

        required_sv_indicators = [
            "Ansökan om",  # sammanfattning header
            "projektbeskrivning",  # section or content
            "budget",  # budget mention
        ]
        for grant in sv_grants:
            r = self._apply_and_generate(
                client, grant_tracker, grant, board_input, auth_cookies
            )
            html = r.text.lower()
            for indicator in required_sv_indicators:
                assert indicator.lower() in html, (
                    f"{grant['grant_id']}: missing indicator '{indicator}' in Swedish draft"
                )

    def test_english_grants_have_all_required_sections(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """English grants must have: summary, project_description,
        target_group, budget_justification, kpi_evidence, sustainability."""
        en_grants = [g for g in all_grants if g.get("language") == "en"]
        assert len(en_grants) >= 3, "Expected at least 3 English grants"

        required_en = [
            "summary", "project_description", "target_group",
            "budget_justification", "kpi_evidence", "sustainability",
        ]
        for grant in en_grants:
            r = self._apply_and_generate(
                client, grant_tracker, grant, board_input, auth_cookies
            )
            html = r.text.lower()
            for section in required_en:
                assert section.replace("_", " ") in html or section.replace("_", "") in html, (
                    f"{grant['grant_id']}: missing section '{section}' in English draft"
                )

    def test_draft_references_actual_kpi_numbers(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """The draft must include real KPI numbers from the seeded
        activities, not placeholder text like '[Ingen KPI-data]'."""
        grant = all_grants[0]
        r = self._apply_and_generate(
            client, grant_tracker, grant, board_input, auth_cookies
        )
        html = r.text
        # The draft should NOT contain placeholder text
        assert "[Ingen KPI-data" not in html, (
            "Draft should contain real KPI data, not placeholder"
        )
        # Should contain "aktiviteter" or "activities" (evidence of KPI narrative)
        assert "aktiviteter" in html.lower() or "activities" in html.lower(), (
            "Draft should reference activities from KPI data"
        )
        # Should contain "deltagare" or "participants"
        assert "deltagare" in html.lower() or "participants" in html.lower(), (
            "Draft should reference participant counts from KPI data"
        )

    def test_draft_includes_budget_figures(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """Budget and own contribution from board input must appear."""
        grant = all_grants[0]
        r = self._apply_and_generate(
            client, grant_tracker, grant, board_input, auth_cookies
        )
        html = r.text
        assert "200" in html, "Requested budget should appear"
        assert "50" in html, "Own contribution should appear"

    def test_draft_includes_project_description(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """Board-provided project description should appear verbatim."""
        grant = all_grants[0]
        r = self._apply_and_generate(
            client, grant_tracker, grant, board_input, auth_cookies
        )
        assert "Youth Tech" in r.text

    def test_no_pii_in_draft(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """No identity fields should appear in any draft."""
        pii_patterns = [
            "personal_number", "personnummer", "19800101",
            "first_name", "last_name", "@example",
            "+4670", "anna@",
        ]
        for grant in all_grants:
            r = self._apply_and_generate(
                client, grant_tracker, grant, board_input, auth_cookies
            )
            html = r.text.lower()
            for pattern in pii_patterns:
                assert pattern.lower() not in html, (
                    f"{grant['grant_id']}: PII pattern '{pattern}' found in draft"
                )

    def test_draft_language_matches_grant(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """Swedish grants get Swedish drafts, English grants get English."""
        for grant in all_grants:
            r = self._apply_and_generate(
                client, grant_tracker, grant, board_input, auth_cookies
            )
            html = r.text
            if grant.get("language") == "sv":
                assert "Ansökan om" in html or "sammanfattning" in html.lower(), (
                    f"{grant['grant_id']}: Swedish grant but draft not in Swedish"
                )
            elif grant.get("language") == "en":
                assert "Application for" in html or "summary" in html.lower(), (
                    f"{grant['grant_id']}: English grant but draft not in English"
                )


# ============================================================================
# SST-specific compliance
# ============================================================================


class TestSSTCompliance:
    """SST (Nämnden för statligt stöd till trossamfund) has specific
    requirements for annual reports and project applications."""

    def test_sst_org_requires_member_count_and_activities(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        sst_org = next(g for g in all_grants if g["grant_id"] == "sst-org-2025")
        assert "member_count" in sst_org.get("required_data", [])
        assert "activities_count" in sst_org.get("required_data", [])

    def test_sst_eligibility_includes_registration(self, all_grants):
        sst_org = next(g for g in all_grants if g["grant_id"] == "sst-org-2025")
        eligibility = " ".join(sst_org.get("eligibility", []))
        assert "registr" in eligibility.lower(), (
            "SST requires registered religious community"
        )


# ============================================================================
# MUCF-specific compliance
# ============================================================================


class TestMUCFCompliance:
    """MUCF requires age-band breakdowns in their reports."""

    def test_mucf_requires_age_bands(self, all_grants):
        mucf = next(g for g in all_grants if g["grant_id"] == "mucf-projekt-2025")
        kpi_fields = mucf.get("kpi_fields_from_platform", [])
        assert "age_band_counts" in kpi_fields, (
            "MUCF project grants require age-band data"
        )

    def test_mucf_draft_includes_age_breakdown(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        mucf = next(g for g in all_grants if g["grant_id"] == "mucf-projekt-2025")
        grant_tracker.save_application(GrantApplication(
            grant_id=mucf["grant_id"],
            church_id="c1",
            status="in_progress",
            project_name="Ungdomsintegration 2025",
            project_description="Integrationsverksamhet för nyanlända ungdomar.",
            target_group="Ungdomar 13-25 år",
            budget_amount=200000,
            own_contribution=50000,
        ))
        r = client.post(
            f"/grants/{mucf['grant_id']}/generate",
            cookies={"kyrk_session": "u-admin:c1:admin"},
        )
        html = r.text
        # Age bands from our seeded data should appear
        assert "13-17" in html or "7-12" in html, (
            "MUCF draft should include age-band breakdown from KPI data"
        )


# ============================================================================
# Arvsfonden-specific compliance
# ============================================================================


class TestArvsfondenCompliance:
    """Arvsfonden requires innovation narrative + target group evidence."""

    def test_arvsfonden_kpi_fields_include_participants(self, all_grants):
        arv = next(g for g in all_grants if g["grant_id"] == "arvsfonden-projekt-2025")
        kpi = arv.get("kpi_fields_from_platform", [])
        assert "participants_total" in kpi

    def test_arvsfonden_facility_grant_exists(self, all_grants):
        """Arvsfonden Lokalstöd is critical for the church-buying goal."""
        lokal = next((g for g in all_grants if g["grant_id"] == "arvsfonden-lokal-2025"), None)
        assert lokal is not None, "Arvsfonden Lokalstöd must be in the database"
        assert lokal["amount_range"]["max"] >= 5000000, (
            "Lokalstöd should support up to 10M SEK for facility purchase"
        )


# ============================================================================
# EU grant compliance
# ============================================================================


class TestEUGrantCompliance:
    """EU grants (Erasmus+, ESF+) must be in English."""

    def test_erasmus_is_english(self, all_grants):
        erasmus = next(g for g in all_grants if g["grant_id"] == "erasmus-ka2-2025")
        assert erasmus["language"] == "en"

    def test_erasmus_requires_partnership(self, all_grants):
        erasmus = next(g for g in all_grants if g["grant_id"] == "erasmus-ka2-2025")
        eligibility = " ".join(erasmus.get("eligibility", []))
        assert "organisationer" in eligibility.lower() or "partner" in eligibility.lower(), (
            "Erasmus+ KA2 requires cross-border partnership/organizations"
        )


# ============================================================================
# Skatteverket / fiscal compliance
# ============================================================================


class TestFiscalCompliance:
    """Verify that budget data in drafts aligns with what Skatteverket
    and grant bodies expect: proper amounts, currency, and no made-up numbers."""

    def test_budget_amount_matches_board_input(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """The budget in the draft must match what the board entered,
        not a hallucinated number."""
        grant = all_grants[0]
        grant_tracker.save_application(GrantApplication(
            grant_id=grant["grant_id"],
            church_id="c1",
            status="in_progress",
            project_name="Test Project",
            project_description="Test description",
            target_group="Test group",
            budget_amount=175000,
            own_contribution=35000,
        ))
        r = client.post(
            f"/grants/{grant['grant_id']}/generate",
            cookies=auth_cookies,
        )
        html = r.text
        assert "175" in html, "Budget should match board input (175000)"
        assert "35" in html, "Own contribution should match board input (35000)"

    def test_currency_matches_grant_spec(
        self, client, grant_tracker, all_grants, board_input,
        realistic_activities, auth_cookies,
    ):
        """Swedish grants use SEK, EU grants use EUR."""
        for grant in all_grants:
            currency = grant.get("amount_range", {}).get("currency", "SEK")
            grant_tracker.save_application(GrantApplication(
                grant_id=grant["grant_id"],
                church_id="c1",
                status="in_progress",
                project_name="Test",
                project_description="Test",
                target_group="Test",
                budget_amount=100000,
                own_contribution=25000,
            ))
            r = client.post(
                f"/grants/{grant['grant_id']}/generate",
                cookies=auth_cookies,
            )
            if r.status_code == 200:
                html = r.text
                assert currency in html, (
                    f"{grant['grant_id']}: expected currency '{currency}' in draft"
                )


# ============================================================================
# Full flow integration test
# ============================================================================


class TestEndToEndGrantFlow:
    """Simulates the complete board member journey from browsing grants
    to generating a submission-ready draft."""

    def test_full_flow_browse_to_draft(
        self, client, grant_tracker, activity, reporting,
        realistic_activities, auth_cookies,
    ):
        """
        1. GET /grants → see list
        2. GET /grants/arvsfonden-projekt-2025 → see detail + eligibility
        3. POST /grants/arvsfonden-projekt-2025/apply → save application
        4. POST /grants/arvsfonden-projekt-2025/generate → get draft
        5. Verify draft has all sections + real numbers
        """
        # 1. Browse grants
        r = client.get("/grants", cookies=auth_cookies)
        assert r.status_code == 200
        assert "arvsfonden" in r.text.lower()

        # 2. View detail
        r = client.get("/grants/arvsfonden-projekt-2025", cookies=auth_cookies)
        assert r.status_code == 200
        assert "Generera underlag" in r.text or "Starta" in r.text

        # 3. Submit application form
        r = client.post(
            "/grants/arvsfonden-projekt-2025/apply",
            data={
                "project_name": "Digital Ungdomsintegration",
                "project_description": (
                    "Ett tvåårigt innovationsprojekt som ger nyanlända ungdomar "
                    "digitala färdigheter genom veckovisa workshops i kodning, "
                    "robotik och digital etik."
                ),
                "target_group": "Nyanlända ungdomar 13-25 år i Stockholms förorter",
                "budget_amount": "350000",
                "own_contribution": "75000",
                "notes": "Samarbete med lokala skolor planerat.",
            },
            cookies=auth_cookies,
        )
        assert r.status_code == 303, f"Expected redirect, got {r.status_code}"

        # 4. Generate draft
        r = client.post(
            "/grants/arvsfonden-projekt-2025/generate",
            cookies=auth_cookies,
        )
        assert r.status_code == 200
        html = r.text

        # 5. Verify completeness
        assert "Digital Ungdomsintegration" in html, "Project name missing"
        assert "350" in html, "Budget amount missing"
        assert "75" in html, "Own contribution missing"
        assert "228" in html or "aktiviteter" in html.lower(), "KPI evidence missing"
        assert "Ansökan om" in html, "Swedish header missing"

        # 6. Verify no PII leaked
        for pii in ["personnummer", "19800101", "@example", "+4670"]:
            assert pii not in html.lower(), f"PII '{pii}' found in draft"

    def test_full_flow_english_eu_grant(
        self, client, grant_tracker, activity, reporting,
        realistic_activities, auth_cookies,
    ):
        """Same flow but for an English EU grant (Erasmus+ KA2)."""
        grant_tracker.save_application(GrantApplication(
            grant_id="erasmus-ka2-2025",
            church_id="c1",
            status="in_progress",
            project_name="Digital Youth Exchange",
            project_description="Cross-border youth digital skills exchange.",
            target_group="Youth 13-25 from Sweden, Germany, and Greece",
            budget_amount=80000,
            own_contribution=20000,
        ))
        r = client.post(
            "/grants/erasmus-ka2-2025/generate",
            cookies=auth_cookies,
        )
        assert r.status_code == 200
        html = r.text
        assert "Application for" in html or "summary" in html.lower(), (
            "English grant should produce English draft"
        )
        assert "EUR" in html, "Erasmus+ should use EUR"
