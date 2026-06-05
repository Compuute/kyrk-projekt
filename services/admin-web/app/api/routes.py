"""HTML routes. Each route either renders a template or redirects."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_activity_client,
    get_certificate_client,
    get_grant_tracker,
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
from app.ports.grant_tracker import GrantApplication, GrantTrackerPort


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


# -------------------------------------------------------------------- grants


def _load_grant_database() -> list[dict]:
    """Load the grant catalog from automation/grants/database.json."""
    db_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "automation" / "grants" / "database.json"
    if not db_path.exists():
        return []
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("grants", [])


def _deadline_color(deadline_str: str) -> str:
    """Return 'green', 'yellow', or 'red' based on days until deadline."""
    try:
        deadline = date.fromisoformat(deadline_str)
    except (ValueError, TypeError):
        return "green"
    days = (deadline - date.today()).days
    if days < 30:
        return "red"
    if days < 60:
        return "yellow"
    return "green"


def _country_flag(country: str) -> str:
    flags = {
        "SE": "\U0001f1f8\U0001f1ea",
        "EU": "\U0001f1ea\U0001f1fa",
        "NO": "\U0001f1f3\U0001f1f4",
        "NR": "\U0001f1f3\U0001f1f4",  # Nordic — use NO flag as proxy
    }
    return flags.get(country, "")


STATUS_LABELS = {
    "not_started": "Ej startad",
    "in_progress": "Pågår",
    "submitted": "Inskickad",
    "approved": "Beviljad",
    "rejected": "Avslagen",
}


@router.get("/grants", response_class=HTMLResponse)
def grants_list(
    request: Request,
    flash: str | None = None,
    level: str = "success",
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    grants = _load_grant_database()
    applications = {a.grant_id: a for a in tracker.list_applications(session.church_id)}

    enriched = []
    upcoming_deadlines = 0
    for g in grants:
        app = applications.get(g["grant_id"])
        app_status = app.status if app else "not_started"
        color = _deadline_color(g.get("next_deadline", ""))
        if color in ("red", "yellow"):
            upcoming_deadlines += 1
        enriched.append({
            **g,
            "app_status": app_status,
            "app_status_label": STATUS_LABELS.get(app_status, app_status),
            "deadline_color": color,
            "country_flag": _country_flag(g.get("country", "")),
            "amount_display": _format_amount(g.get("amount_range", {})),
        })

    return TEMPLATES.TemplateResponse(
        request=request,
        name="grants_list.html",
        context={
            "session": session,
            "grants": enriched,
            "upcoming_deadlines": upcoming_deadlines,
            "flash": flash,
            "level": level,
        },
    )


def _format_amount(amount_range: dict) -> str:
    cur = amount_range.get("currency", "SEK")
    lo = amount_range.get("min", 0)
    hi = amount_range.get("max", 0)
    return f"{lo:,.0f} - {hi:,.0f} {cur}".replace(",", " ")


@router.get("/grants/{grant_id}", response_class=HTMLResponse)
def grant_detail(
    grant_id: str,
    request: Request,
    flash: str | None = None,
    level: str = "success",
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    grants = _load_grant_database()
    grant = next((g for g in grants if g["grant_id"] == grant_id), None)
    if grant is None:
        return _flash_redirect("/grants", "Bidraget hittades inte", level="error")

    app = tracker.get_application(session.church_id, grant_id)

    # Check which eligibility items the platform can verify
    platform_fields = set(grant.get("kpi_fields_from_platform", []))
    eligibility_checks = []
    for item in grant.get("eligibility", []):
        eligibility_checks.append({
            "text": item,
            "auto": bool(platform_fields),  # simplified: platform has data
        })

    return TEMPLATES.TemplateResponse(
        request=request,
        name="grant_detail.html",
        context={
            "session": session,
            "grant": grant,
            "application": app,
            "app_status_label": STATUS_LABELS.get(app.status if app else "not_started", "Ej startad"),
            "eligibility_checks": eligibility_checks,
            "deadline_color": _deadline_color(grant.get("next_deadline", "")),
            "country_flag": _country_flag(grant.get("country", "")),
            "amount_display": _format_amount(grant.get("amount_range", {})),
            "flash": flash,
            "level": level,
        },
    )


@router.get("/grants/{grant_id}/apply", response_class=HTMLResponse)
def grant_application_form(
    grant_id: str,
    request: Request,
    flash: str | None = None,
    level: str = "success",
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    grants = _load_grant_database()
    grant = next((g for g in grants if g["grant_id"] == grant_id), None)
    if grant is None:
        return _flash_redirect("/grants", "Bidraget hittades inte", level="error")

    app = tracker.get_application(session.church_id, grant_id)

    return TEMPLATES.TemplateResponse(
        request=request,
        name="grant_application_form.html",
        context={
            "session": session,
            "grant": grant,
            "application": app,
            "flash": flash,
            "level": level,
        },
    )


@router.post("/grants/{grant_id}/apply")
def grant_application_save(
    grant_id: str,
    request: Request,
    project_name: str = Form(""),
    project_description: str = Form(""),
    target_group: str = Form(""),
    budget_amount: float = Form(0.0),
    own_contribution: float = Form(0.0),
    notes: str = Form(""),
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    existing = tracker.get_application(session.church_id, grant_id)
    app = existing or GrantApplication(grant_id=grant_id, church_id=session.church_id)
    app.project_name = project_name
    app.project_description = project_description
    app.target_group = target_group
    app.budget_amount = budget_amount if budget_amount else None
    app.own_contribution = own_contribution if own_contribution else None
    app.notes = notes
    if app.status == "not_started":
        app.status = "in_progress"
        app.started_at = datetime.utcnow()
    tracker.save_application(app)

    return _flash_redirect(
        f"/grants/{grant_id}",
        "Ansökningsunderlag sparat",
        level="success",
    )


@router.post("/grants/{grant_id}/generate", response_class=HTMLResponse)
def grant_generate_draft(
    grant_id: str,
    request: Request,
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
    activity: ActivityClientPort = Depends(get_activity_client),
    reporting: ReportingClientPort = Depends(get_reporting_client),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    grants = _load_grant_database()
    grant = next((g for g in grants if g["grant_id"] == grant_id), None)
    if grant is None:
        return _flash_redirect("/grants", "Bidraget hittades inte", level="error")

    app = tracker.get_application(session.church_id, grant_id)

    # Fetch KPI data from the last 12 months
    today = date.today()
    start = f"{today.year - 1:04d}-{today.month:02d}-01"
    end = today.isoformat()

    error_message: str | None = None
    kpi_data: dict | None = None
    try:
        aggregates = activity.export_period(session.token, start, end)
        activities_payload = [asdict(a) for a in aggregates]
        total_participants = sum(a.get("participants_total", 0) for a in activities_payload)
        total_activities = len(activities_payload)
        age_bands: dict[str, int] = {}
        for a in activities_payload:
            for band, n in a.get("age_band_counts", {}).items():
                age_bands[band] = age_bands.get(band, 0) + n
        kpi_data = {
            "participants_total": total_participants,
            "activities_count": total_activities,
            "age_band_counts": age_bands,
        }
    except ClientError as exc:
        error_message = f"Kunde inte hämta KPI-data: {exc}"

    # Build the draft sections from board input + KPI data
    draft = _build_grant_draft(grant, app, kpi_data, error_message)

    return TEMPLATES.TemplateResponse(
        request=request,
        name="grant_draft_result.html",
        context={
            "session": session,
            "grant": grant,
            "application": app,
            "draft": draft,
            "error_message": error_message,
        },
    )


def _build_grant_draft(
    grant: dict,
    app: GrantApplication | None,
    kpi_data: dict | None,
    error_message: str | None,
) -> dict:
    """Build a structured grant draft from board input and KPI data."""
    lang = grant.get("language", "sv")
    project_name = app.project_name if app else ""
    project_desc = app.project_description if app else ""
    target_group = app.target_group if app else ""
    budget = app.budget_amount if app else None
    own = app.own_contribution if app else None

    kpi_summary = ""
    if kpi_data:
        kpi_summary = (
            f"Under de senaste 12 månaderna har organisationen genomfört "
            f"{kpi_data['activities_count']} aktiviteter med totalt "
            f"{kpi_data['participants_total']} deltagare."
        )
        if kpi_data.get("age_band_counts"):
            age_parts = [f"{band}: {n}" for band, n in kpi_data["age_band_counts"].items() if n > 0]
            if age_parts:
                kpi_summary += f" Åldersfördelning: {', '.join(age_parts)}."

    if lang == "en":
        return {
            "summary": f"Application for {grant.get('name_en', grant['name'])} — {project_name}" if project_name else f"Application for {grant.get('name_en', grant['name'])}",
            "project_description": project_desc or "[Fill in project description]",
            "target_group": target_group or "[Fill in target group]",
            "method": "[Describe the method and approach]",
            "expected_results": "[Describe the expected results and impact]",
            "budget_justification": f"Requested amount: {budget:,.0f} {grant.get('amount_range', {}).get('currency', 'SEK')}" if budget else "[Fill in budget]",
            "kpi_evidence": kpi_summary.replace("månaderna", "months").replace("aktiviteter", "activities").replace("deltagare", "participants").replace("organisationen genomfört", "the organization conducted").replace("Under de senaste 12", "Over the past 12").replace("med totalt", "with a total of") if kpi_summary else "[No KPI data available]",
            "sustainability": "[Describe how the project results will be sustained after funding ends]",
        }

    return {
        "sammanfattning": f"Ansökan om {grant['name']} — {project_name}" if project_name else f"Ansökan om {grant['name']}",
        "projektbeskrivning": project_desc or "[Fyll i projektbeskrivning]",
        "målgrupp": target_group or "[Fyll i målgrupp]",
        "metod": "[Beskriv metod och tillvägagångssätt]",
        "förväntade_resultat": "[Beskriv förväntade resultat och påverkan]",
        "budget_motivering": f"Sökt belopp: {budget:,.0f} {grant.get('amount_range', {}).get('currency', 'SEK')}. Egen insats: {own:,.0f} {grant.get('amount_range', {}).get('currency', 'SEK')}." if budget and own else "[Fyll i budget]",
        "kpi_underlag": kpi_summary or "[Ingen KPI-data tillgänglig]",
        "hållbarhet": "[Beskriv hur projektets resultat fortsätter efter bidragsperioden]",
    }


@router.get("/grants/{grant_id}/status", response_class=HTMLResponse)
def grant_status(
    grant_id: str,
    request: Request,
    flash: str | None = None,
    level: str = "success",
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    grants = _load_grant_database()
    grant = next((g for g in grants if g["grant_id"] == grant_id), None)
    if grant is None:
        return _flash_redirect("/grants", "Bidraget hittades inte", level="error")

    app = tracker.get_application(session.church_id, grant_id)

    return TEMPLATES.TemplateResponse(
        request=request,
        name="grant_detail.html",
        context={
            "session": session,
            "grant": grant,
            "application": app,
            "app_status_label": STATUS_LABELS.get(app.status if app else "not_started", "Ej startad"),
            "eligibility_checks": [],
            "deadline_color": _deadline_color(grant.get("next_deadline", "")),
            "country_flag": _country_flag(grant.get("country", "")),
            "amount_display": _format_amount(grant.get("amount_range", {})),
            "flash": flash,
            "level": level,
        },
    )


@router.post("/grants/{grant_id}/status")
def grant_status_update(
    grant_id: str,
    request: Request,
    new_status: str = Form(...),
    amount_requested: float = Form(0.0),
    amount_granted: float = Form(0.0),
    notes: str = Form(""),
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    valid_statuses = {"not_started", "in_progress", "submitted", "approved", "rejected"}
    if new_status not in valid_statuses:
        return _flash_redirect(f"/grants/{grant_id}", "Ogiltig status", level="error")

    existing = tracker.get_application(session.church_id, grant_id)
    app = existing or GrantApplication(grant_id=grant_id, church_id=session.church_id)
    app.status = new_status
    if new_status == "submitted" and app.submitted_at is None:
        app.submitted_at = datetime.utcnow()
    if new_status == "in_progress" and app.started_at is None:
        app.started_at = datetime.utcnow()
    if amount_requested:
        app.amount_requested = amount_requested
    if amount_granted:
        app.amount_granted = amount_granted
    if notes:
        app.notes = notes
    tracker.save_application(app)

    return _flash_redirect(
        f"/grants/{grant_id}",
        f"Status uppdaterad till: {STATUS_LABELS.get(new_status, new_status)}",
        level="success",
    )


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
