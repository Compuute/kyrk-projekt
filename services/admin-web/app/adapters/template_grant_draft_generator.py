"""Deterministic, template-based grant draft generator.

No external calls. Builds a structured draft from board input + KPI data with
`[Fyll i …]` placeholders where data is missing. Used as the default in
dev/test and as the fallback when the Claude adapter is unavailable or fails.
"""
from __future__ import annotations

from app.ports.grant_tracker import GrantApplication


class TemplateGrantDraftGenerator:
    def generate(
        self,
        grant: dict,
        application: GrantApplication | None,
        kpi_data: dict | None,
        lang: str,
    ) -> dict:
        app = application
        project_name = app.project_name if app else ""
        project_desc = app.project_description if app else ""
        target_group = app.target_group if app else ""
        budget = app.budget_amount if app else None
        own = app.own_contribution if app else None
        currency = grant.get("amount_range", {}).get("currency", "SEK")

        kpi_summary = ""
        if kpi_data:
            kpi_summary = (
                f"Under de senaste 12 månaderna har organisationen genomfört "
                f"{kpi_data['activities_count']} aktiviteter med totalt "
                f"{kpi_data['participants_total']} deltagare."
            )
            if kpi_data.get("age_band_counts"):
                age_parts = [
                    f"{band}: {n}"
                    for band, n in kpi_data["age_band_counts"].items()
                    if n > 0
                ]
                if age_parts:
                    kpi_summary += f" Åldersfördelning: {', '.join(age_parts)}."

        if lang == "en":
            name = grant.get("name_en", grant["name"])
            return {
                "summary": f"Application for {name} — {project_name}" if project_name else f"Application for {name}",
                "project_description": project_desc or "[Fill in project description]",
                "target_group": target_group or "[Fill in target group]",
                "method": "[Describe the method and approach]",
                "expected_results": "[Describe the expected results and impact]",
                "budget_justification": f"Requested amount: {budget:,.0f} {currency}" if budget else "[Fill in budget]",
                "kpi_evidence": (
                    kpi_summary.replace("månaderna", "months")
                    .replace("aktiviteter", "activities")
                    .replace("deltagare", "participants")
                    .replace("organisationen genomfört", "the organization conducted")
                    .replace("Under de senaste 12", "Over the past 12")
                    .replace("med totalt", "with a total of")
                    if kpi_summary
                    else "[No KPI data available]"
                ),
                "sustainability": "[Describe how the project results will be sustained after funding ends]",
            }

        return {
            "sammanfattning": f"Ansökan om {grant['name']} — {project_name}" if project_name else f"Ansökan om {grant['name']}",
            "projektbeskrivning": project_desc or "[Fyll i projektbeskrivning]",
            "målgrupp": target_group or "[Fyll i målgrupp]",
            "metod": "[Beskriv metod och tillvägagångssätt]",
            "förväntade_resultat": "[Beskriv förväntade resultat och påverkan]",
            "budget_motivering": f"Sökt belopp: {budget:,.0f} {currency}. Egen insats: {own:,.0f} {currency}." if budget and own else "[Fyll i budget]",
            "kpi_underlag": kpi_summary or "[Ingen KPI-data tillgänglig]",
            "hållbarhet": "[Beskriv hur projektets resultat fortsätter efter bidragsperioden]",
        }
