"""Reporting use cases. YELLOW-only — enforced at ingress by the PII guard."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.errors import NotAuthorized, ReportNotFound
from app.domain.models import Actor, Report, ReportKind, Role
from app.domain.pii_guard import assert_no_pii
from app.ports.report_repository import ReportRepository


_WRITE_ROLES: set[Role] = {Role.ADMIN}  # service-account role or admin
_READ_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY, Role.VIEWER}


@dataclass(frozen=True)
class GenerateReportInput:
    kind: ReportKind
    period: str
    activities: list[dict]
    finance: dict


class ReportingService:
    def __init__(self, repo: ReportRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------ writes

    def generate(self, actor: Actor, data: GenerateReportInput) -> Report:
        self._require_role(actor, _WRITE_ROLES)
        # Defense-in-depth: validate that the incoming payload carries no PII.
        assert_no_pii({"activities": data.activities, "finance": data.finance})

        if data.kind is ReportKind.MONTHLY:
            payload = self._monthly(data)
        elif data.kind is ReportKind.QUARTERLY:
            payload = self._quarterly(data)
        else:
            payload = self._board_export(data)

        report = Report(
            church_id=actor.church_id,
            kind=data.kind,
            period=data.period,
            payload=payload,
        )
        self._repo.add(report)
        return report

    # ------------------------------------------------------------------- reads

    def get(self, actor: Actor, report_id: str) -> Report:
        self._require_role(actor, _READ_ROLES)
        report = self._repo.get(actor.church_id, report_id)
        if report is None:
            raise ReportNotFound(report_id)
        return report

    # ------------------------------------------------------------- aggregation

    def _monthly(self, data: GenerateReportInput) -> dict:
        total_participants = sum(a.get("participants_total", 0) for a in data.activities)
        by_type: dict[str, int] = {}
        by_age: dict[str, int] = {}
        for a in data.activities:
            by_type[a["activity_type"]] = by_type.get(a["activity_type"], 0) + a.get("participants_total", 0)
            for band, n in a.get("age_band_counts", {}).items():
                by_age[band] = by_age.get(band, 0) + n

        operating_cost = float(data.finance.get("operating_cost", 0.0))
        grants = float(data.finance.get("grants", 0.0))
        own = float(data.finance.get("own_contribution", 0.0))

        cost_per_participant = (
            operating_cost / total_participants if total_participants > 0 else None
        )
        grant_leverage = grants / own if own > 0 else None

        return {
            "period": data.period,
            "activities_count": len(data.activities),
            "participants_total": total_participants,
            "participants_by_type": by_type,
            "participants_by_age_band": by_age,
            "cost_per_participant": cost_per_participant,
            "grant_leverage_ratio": grant_leverage,
        }

    def _quarterly(self, data: GenerateReportInput) -> dict:
        monthly_like = self._monthly(data)
        return {
            **monthly_like,
            "variance_input": True,  # hint to OpenClaw prompt
        }

    def _board_export(self, data: GenerateReportInput) -> dict:
        base = self._monthly(data)
        return {
            "period": data.period,
            "summary": {
                "participants_total": base["participants_total"],
                "activities_count": base["activities_count"],
                "cost_per_participant": base["cost_per_participant"],
                "grant_leverage_ratio": base["grant_leverage_ratio"],
            },
            "breakdown": {
                "by_type": base["participants_by_type"],
                "by_age_band": base["participants_by_age_band"],
            },
            "openclaw_ready": True,
        }

    # --------------------------------------------------------------- internals

    def _require_role(self, actor: Actor, allowed: set[Role]) -> None:
        if actor.role not in allowed:
            raise NotAuthorized(f"role {actor.role.value} cannot perform this action")
