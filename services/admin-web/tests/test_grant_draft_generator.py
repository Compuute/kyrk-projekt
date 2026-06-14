"""Tests for the grant draft generators (template + Claude adapter)."""
from __future__ import annotations

import pytest

from app.adapters.anthropic_grant_draft_generator import AnthropicGrantDraftGenerator
from app.adapters.template_grant_draft_generator import TemplateGrantDraftGenerator
from app.domain.grant_pii_guard import GrantPIIRejected, assert_no_pii
from app.ports.grant_tracker import GrantApplication

_SV_SECTIONS = {
    "sammanfattning", "projektbeskrivning", "målgrupp", "metod",
    "förväntade_resultat", "budget_motivering", "kpi_underlag", "hållbarhet",
}
_EN_SECTIONS = {
    "summary", "project_description", "target_group", "method",
    "expected_results", "budget_justification", "kpi_evidence", "sustainability",
}


def _grant(lang="sv"):
    return {
        "grant_id": "sst-org-2025",
        "name": "SST Organisationsstöd",
        "name_en": "SST Organisation Grant",
        "language": lang,
        "eligibility": ["Registrerat trossamfund hos SST"],
        "required_data": ["member_count", "activities_count"],
        "amount_range": {"currency": "SEK", "min": 50000, "max": 2000000},
        "notes_sv": "Primär finansiär för trossamfund.",
    }


def _app(**kw):
    base = dict(grant_id="sst-org-2025", church_id="c1", project_name="Ungdomsläger")
    base.update(kw)
    return GrantApplication(**base)


_KPI = {"participants_total": 120, "activities_count": 18, "age_band_counts": {"0-12": 40, "13-25": 50}}


# --------------------------------------------------------------- PII guard


def test_pii_guard_rejects_personnummer():
    with pytest.raises(GrantPIIRejected):
        assert_no_pii({"project_description": "Kontakta 19900101-1234 för info"})


def test_pii_guard_allows_clean_text_and_amounts():
    assert_no_pii({"desc": "Vi sökte 2000000 kr för 18 aktiviteter", "n": 120})


# ---------------------------------------------------------- template adapter


def test_template_returns_all_sv_sections():
    draft = TemplateGrantDraftGenerator().generate(_grant("sv"), _app(), _KPI, "sv")
    assert set(draft.keys()) == _SV_SECTIONS
    assert "18 aktiviteter" in draft["kpi_underlag"]


def test_template_returns_all_en_sections():
    draft = TemplateGrantDraftGenerator().generate(_grant("en"), _app(), _KPI, "en")
    assert set(draft.keys()) == _EN_SECTIONS


# ----------------------------------------------------------- Claude adapter


class _FakeMessage:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]


class _FakeClient:
    def __init__(self, text):
        self._text = text
        self.calls: list[dict] = []

    @property
    def messages(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeMessage(self._text)


def test_claude_overlays_llm_prose_on_all_sections():
    llm_json = (
        '{"sammanfattning":"AI-sammanfattning","projektbeskrivning":"AI-beskrivning",'
        '"målgrupp":"unga","metod":"workshops","förväntade_resultat":"fler deltagare",'
        '"budget_motivering":"motiverad budget","kpi_underlag":"120 deltagare",'
        '"hållbarhet":"lever vidare"}'
    )
    client = _FakeClient(llm_json)
    gen = AnthropicGrantDraftGenerator(api_key="k", model="m", client=client, self_review=False)
    draft = gen.generate(_grant("sv"), _app(), _KPI, "sv")
    assert set(draft.keys()) == _SV_SECTIONS
    assert draft["projektbeskrivning"] == "AI-beskrivning"
    assert client.calls and client.calls[0]["model"] == "m"


def test_claude_keeps_template_section_when_llm_omits_it():
    # LLM returns only one section; the rest must remain from the template.
    client = _FakeClient('{"sammanfattning":"bara denna"}')
    gen = AnthropicGrantDraftGenerator(api_key="k", model="m", client=client, self_review=False)
    draft = gen.generate(_grant("sv"), _app(), _KPI, "sv")
    assert draft["sammanfattning"] == "bara denna"
    assert set(draft.keys()) == _SV_SECTIONS
    assert "18 aktiviteter" in draft["kpi_underlag"]  # template value preserved


def test_claude_falls_back_to_template_on_client_error():
    class _Boom:
        @property
        def messages(self):
            return self

        def create(self, **kwargs):
            raise RuntimeError("api down")

    gen = AnthropicGrantDraftGenerator(api_key="k", model="m", client=_Boom(), self_review=False)
    draft = gen.generate(_grant("sv"), _app(), _KPI, "sv")
    # Identical to the deterministic template output.
    assert draft == TemplateGrantDraftGenerator().generate(_grant("sv"), _app(), _KPI, "sv")


def test_claude_does_not_call_llm_when_pii_present():
    client = _FakeClient('{"sammanfattning":"x"}')
    gen = AnthropicGrantDraftGenerator(api_key="k", model="m", client=client, self_review=False)
    app = _app(project_description="Ring 19900101-1234")
    draft = gen.generate(_grant("sv"), app, _KPI, "sv")
    assert client.calls == []  # PII guard blocked the call
    assert draft == TemplateGrantDraftGenerator().generate(_grant("sv"), app, _KPI, "sv")


def test_claude_runs_self_review_second_pass():
    client = _FakeClient('{"sammanfattning":"granskad"}')
    gen = AnthropicGrantDraftGenerator(api_key="k", model="m", client=client, self_review=True)
    gen.generate(_grant("sv"), _app(), _KPI, "sv")
    assert len(client.calls) == 2  # generation + review
