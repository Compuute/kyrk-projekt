from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import current_actor, get_service
from app.domain.errors import NotAuthorized, PIIRejected, ReportNotFound
from app.domain.models import Actor, Report, ReportKind
from app.services.reporting_service import GenerateReportInput, ReportingService


router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    period: str = Field(min_length=4, max_length=16)
    activities: list[dict]
    finance: dict


class ReportResponse(BaseModel):
    report_id: str
    kind: str
    period: str
    payload: dict

    @classmethod
    def from_domain(cls, r: Report) -> "ReportResponse":
        return cls(
            report_id=r.report_id,
            kind=r.kind.value,
            period=r.period,
            payload=r.payload,
        )


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, PIIRejected):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ReportNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error")


def _generate(kind: ReportKind, body: GenerateReportRequest, actor: Actor, svc: ReportingService) -> ReportResponse:
    try:
        report = svc.generate(
            actor,
            GenerateReportInput(
                kind=kind,
                period=body.period,
                activities=body.activities,
                finance=body.finance,
            ),
        )
    except (NotAuthorized, PIIRejected) as exc:
        raise _translate(exc) from exc
    return ReportResponse.from_domain(report)


@router.post("/monthly", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def post_monthly(
    body: GenerateReportRequest,
    actor: Actor = Depends(current_actor),
    svc: ReportingService = Depends(get_service),
) -> ReportResponse:
    return _generate(ReportKind.MONTHLY, body, actor, svc)


@router.post("/quarterly", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def post_quarterly(
    body: GenerateReportRequest,
    actor: Actor = Depends(current_actor),
    svc: ReportingService = Depends(get_service),
) -> ReportResponse:
    return _generate(ReportKind.QUARTERLY, body, actor, svc)


@router.post("/board-export", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def post_board_export(
    body: GenerateReportRequest,
    actor: Actor = Depends(current_actor),
    svc: ReportingService = Depends(get_service),
) -> ReportResponse:
    return _generate(ReportKind.BOARD_EXPORT, body, actor, svc)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    actor: Actor = Depends(current_actor),
    svc: ReportingService = Depends(get_service),
) -> ReportResponse:
    try:
        return ReportResponse.from_domain(svc.get(actor, report_id))
    except (NotAuthorized, ReportNotFound) as exc:
        raise _translate(exc) from exc
