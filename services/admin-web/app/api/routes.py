"""HTML routes. Each route either renders a template or redirects."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_activity_client,
    get_certificate_client,
    get_intake_client,
    get_reporting_client,
    get_session_adapter,
    get_settings,
)
from app.ports.session import SessionInfo, SessionPort
from app.config import Settings
from app.ports.client_errors import ClientError
from app.ports.clients import (
    ActivityClientPort,
    CertificateClientPort,
    IntakeClientPort,
    IssueCertificateRequest,
    ReportingClientPort,
)


router = APIRouter()


def _templates() -> Jinja2Templates:
    # Lazy — so tests that only exercise JSON routes don't force template discovery.
    from pathlib import Path

    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    return Jinja2Templates(directory=str(templates_dir))


TEMPLATES = _templates()


# --------------------------------------------------------------------- helpers


def _require_session(request: Request) -> SessionInfo | RedirectResponse:
    cookie = request.cookies.get("kyrk_session")
    adapter = get_session_adapter()
    info = adapter.validate(cookie)
    if info is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return info


def _flash_redirect(path: str, message: str, level: str = "success") -> RedirectResponse:
    from urllib.parse import quote

    url = f"{path}?flash={quote(message)}&level={level}"
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------------- login


@router.get("/login", response_class=HTMLResponse)
def get_login(request: Request, flash: str | None = None, level: str = "error"):
    return TEMPLATES.TemplateResponse(
        request=request,
        name="login.html",
        context={"flash": flash, "level": level},
    )


@router.post("/login")
def post_login(
    user_id: str = Form(...),
    church_id: str = Form(...),
    role: str = Form(...),
    settings: Settings = Depends(get_settings),
):
    if role not in {"admin", "pastor", "secretary", "viewer"}:
        return _flash_redirect("/login", "unknown role", level="error")
    token = f"{user_id}:{church_id}:{role}"
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return response


@router.post("/logout")
def logout(settings: Settings = Depends(get_settings)):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.cookie_name)
    return response


# ------------------------------------------------------------------ dashboard


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    flash: str | None = None,
    level: str = "success",
    intake: IntakeClientPort = Depends(get_intake_client),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    try:
        pending = intake.list_pending(session.token)
    except ClientError:
        pending = []

    return TEMPLATES.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "session": session,
            "pending_count": len(pending),
            "flash": flash,
            "level": level,
        },
    )


# ---------------------------------------------------------------- submissions


@router.get("/submissions", response_class=HTMLResponse)
def list_submissions(
    request: Request,
    flash: str | None = None,
    level: str = "success",
    intake: IntakeClientPort = Depends(get_intake_client),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    error_message: str | None = None
    try:
        submissions = intake.list_pending(session.token)
    except ClientError as exc:
        submissions = []
        error_message = f"Kunde inte läsa pending submissions: {exc}"

    return TEMPLATES.TemplateResponse(
        request=request,
        name="submissions_list.html",
        context={
            "session": session,
            "submissions": submissions,
            "flash": flash,
            "level": level,
            "error_message": error_message,
        },
    )


@router.post("/submissions/{submission_id}/approve")
def approve_submission(
    submission_id: str,
    request: Request,
    intake: IntakeClientPort = Depends(get_intake_client),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session
    try:
        result = intake.approve(session.token, submission_id)
    except ClientError as exc:
        return _flash_redirect(
            "/submissions", f"Godkännande misslyckades: {exc}", level="error"
        )
    return _flash_redirect(
        "/submissions",
        f"Godkänd. Ny medlem: {result.created_member_id}",
        level="success",
    )


@router.post("/submissions/{submission_id}/reject")
def reject_submission(
    submission_id: str,
    request: Request,
    intake: IntakeClientPort = Depends(get_intake_client),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session
    try:
        intake.reject(session.token, submission_id)
    except ClientError as exc:
        return _flash_redirect(
            "/submissions", f"Avslag misslyckades: {exc}", level="error"
        )
    return _flash_redirect("/submissions", "Avslaget.", level="success")


# ---------------------------------------------------------------- certificates


@router.get("/certificates/new", response_class=HTMLResponse)
def certificate_form(request: Request, flash: str | None = None, level: str = "success"):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    return TEMPLATES.TemplateResponse(
        request=request,
        name="certificates_form.html",
        context={
            "session": session,
            "today": date.today().isoformat(),
            "flash": flash,
            "level": level,
        },
    )


@router.post("/certificates/new")
def issue_certificate(
    request: Request,
    certificate_type: str = Form(...),
    issued_date: str = Form(...),
    member_id: str = Form(...),
    church_name: str = Form(...),
    certs: CertificateClientPort = Depends(get_certificate_client),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    try:
        issued = certs.issue(
            session.token,
            IssueCertificateRequest(
                certificate_type=certificate_type,
                issued_date=issued_date,
                member_id=member_id,
                church_name=church_name,
            ),
        )
    except ClientError as exc:
        return _flash_redirect(
            "/certificates/new",
            f"Utfärdande misslyckades: {exc}",
            level="error",
        )

    return _flash_redirect(
        "/certificates/new",
        f"Utfärdat. Verifieringslänk: {issued.verification_url}",
        level="success",
    )


# ------------------------------------------------------------------- KPI dash


def _month_bounds(period: str) -> tuple[str, str]:
    """Return ISO start and end of a `YYYY-MM` period."""
    year, month = period.split("-")
    y = int(year)
    m = int(month)
    start = f"{y:04d}-{m:02d}-01"
    # last day of month: first day of next month minus one
    if m == 12:
        ny, nm = y + 1, 1
    else:
        ny, nm = y, m + 1
    import calendar

    last = calendar.monthrange(y, m)[1]
    end = f"{y:04d}-{m:02d}-{last:02d}"
    return start, end


@router.get("/kpi", response_class=HTMLResponse)
def kpi_dashboard_form(
    request: Request,
    period: str | None = None,
    flash: str | None = None,
    level: str = "success",
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    today = date.today()
    default_period = period or f"{today.year:04d}-{today.month:02d}"

    return TEMPLATES.TemplateResponse(
        request=request,
        name="kpi_dashboard.html",
        context={
            "session": session,
            "period": default_period,
            "report": None,
            "flash": flash,
            "level": level,
        },
    )


@router.post("/kpi", response_class=HTMLResponse)
def kpi_dashboard_generate(
    request: Request,
    period: str = Form(...),
    operating_cost: float = Form(0.0),
    grants: float = Form(0.0),
    own_contribution: float = Form(0.0),
    activity: ActivityClientPort = Depends(get_activity_client),
    reporting: ReportingClientPort = Depends(get_reporting_client),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    start, end = _month_bounds(period)

    error_message: str | None = None
    report = None
    try:
        aggregates = activity.export_period(session.token, start, end)
        activities_payload = [asdict(a) for a in aggregates]
        report = reporting.generate_monthly(
            token=session.token,
            period=period,
            activities=activities_payload,
            finance={
                "operating_cost": operating_cost,
                "grants": grants,
                "own_contribution": own_contribution,
            },
        )
    except ClientError as exc:
        error_message = f"KPI-genereringen misslyckades: {exc}"

    return TEMPLATES.TemplateResponse(
        request=request,
        name="kpi_dashboard.html",
        context={
            "session": session,
            "period": period,
            "report": report,
            "error_message": error_message,
            "operating_cost": operating_cost,
            "grants": grants,
            "own_contribution": own_contribution,
        },
    )


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
