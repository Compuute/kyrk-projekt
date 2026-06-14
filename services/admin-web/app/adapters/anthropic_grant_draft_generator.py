"""Claude-backed grant draft generator.

Writes funder-tuned application prose grounded in the church's own GREEN data
(aggregate KPIs + board-authored project input) and the funder's public
criteria. A self-review pass tightens the draft against the eligibility
criteria. Lazy-imports the anthropic SDK (vendor code stays in adapters).

Safety rails:
- PII guard: personnummer-like values never leave the service (fallback to
  the local template instead).
- Completeness: the LLM output is merged *over* the template draft, so every
  expected section is always present even if the model omits one.
- Resilience: any failure (import, API, parse) falls back to the deterministic
  template — /generate never 500s and the board always gets a usable draft.
"""
from __future__ import annotations

import json

from app.adapters.template_grant_draft_generator import TemplateGrantDraftGenerator
from app.domain.grant_pii_guard import GrantPIIRejected, assert_no_pii
from app.ports.grant_tracker import GrantApplication

_SYSTEM_PROMPT = (
    "Du är en erfaren bidragsskrivare för ideella organisationer och trossamfund "
    "i Sverige. Du skriver ansökningstext som är konkret, trovärdig och exakt "
    "anpassad till finansiärens uttalade kriterier. Regler: (1) grunda alla "
    "påståenden i den data du får — hitta ALDRIG på siffror, deltagare eller "
    "resultat; (2) där data saknas, skriv kortfattat vad styrelsen behöver "
    "komplettera inom hakparentes; (3) väv in de KPI-bevis som ges; (4) svara "
    "ENDAST med ett JSON-objekt med exakt de nycklar du ombeds fylla, inget annat."
)


class AnthropicGrantDraftGenerator:
    def __init__(
        self,
        api_key: str,
        model: str,
        client=None,
        fallback: TemplateGrantDraftGenerator | None = None,
        self_review: bool = True,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client  # injectable for tests
        self._fallback = fallback or TemplateGrantDraftGenerator()
        self._self_review = self_review

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate(
        self,
        grant: dict,
        application: GrantApplication | None,
        kpi_data: dict | None,
        lang: str,
    ) -> dict:
        # The template draft is always complete; we overlay LLM prose onto it.
        template_draft = self._fallback.generate(grant, application, kpi_data, lang)

        app = application
        inputs = {
            "grant": {
                "name": grant.get("name"),
                "name_en": grant.get("name_en"),
                "eligibility": grant.get("eligibility", []),
                "required_data": grant.get("required_data", []),
                "amount_range": grant.get("amount_range", {}),
                "notes": grant.get("notes_sv") or grant.get("notes_en") or "",
            },
            "board_input": {
                "project_name": app.project_name if app else "",
                "project_description": app.project_description if app else "",
                "target_group": app.target_group if app else "",
                "budget_amount": app.budget_amount if app else None,
                "own_contribution": app.own_contribution if app else None,
            },
            "kpi_data": kpi_data or {},
            "language": lang,
        }

        # Hard PII spärr — never send personnummer-like data to the LLM.
        try:
            assert_no_pii(inputs)
        except GrantPIIRejected:
            return template_draft

        try:
            sections = list(template_draft.keys())
            draft = self._call_model(inputs, sections)
            if self._self_review:
                draft = self._review(inputs, sections, draft)
            # Merge: keep every template section, overlay non-empty LLM prose.
            merged = dict(template_draft)
            for key in sections:
                val = draft.get(key)
                if isinstance(val, str) and val.strip():
                    merged[key] = val.strip()
            return merged
        except Exception:  # noqa: BLE001 — any failure falls back to template
            return template_draft

    def _call_model(self, inputs: dict, sections: list[str]) -> dict:
        client = self._get_client()
        user = (
            "Skriv en bidragsansökan på språket '"
            + inputs["language"]
            + "'. Använd finansiärens kriterier och organisationens data nedan.\n\n"
            + json.dumps(inputs, ensure_ascii=False, indent=2)
            + "\n\nSvara med ETT JSON-objekt med exakt dessa nycklar: "
            + ", ".join(sections)
            + ". Varje värde är färdig prosa för den sektionen."
        )
        message = client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
        )
        return _parse_json(message.content[0].text)

    def _review(self, inputs: dict, sections: list[str], draft: dict) -> dict:
        """Second pass: critique the draft against eligibility and tighten it."""
        client = self._get_client()
        user = (
            "Granska utkastet mot finansiärens kriterier och förbättra det: "
            "säkerställ att varje uttalat behörighets-/bedömningskriterium besvaras, "
            "ta bort ogrundade påståenden, behåll bevisen. Hitta inte på data.\n\n"
            "KRITERIER OCH DATA:\n"
            + json.dumps(inputs, ensure_ascii=False)
            + "\n\nUTKAST:\n"
            + json.dumps(draft, ensure_ascii=False)
            + "\n\nSvara med ETT förbättrat JSON-objekt med exakt dessa nycklar: "
            + ", ".join(sections)
            + "."
        )
        message = client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
        )
        return _parse_json(message.content[0].text)


def _parse_json(text: str) -> dict:
    """Parse a JSON object from the model reply, tolerating fenced code blocks."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model reply")
    return json.loads(text[start : end + 1])
