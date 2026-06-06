"""HTML routes. Each route either renders a template or redirects."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import (
    get_activity_client,
    get_certificate_client,
    get_content_store,
    get_funeral_tracker,
    get_grant_tracker,
    get_intake_client,
    get_reporting_client,
    get_session_adapter,
    get_settings,
    get_translator,
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
from app.ports.content_store import ContentStorePort
from app.ports.funeral_tracker import (
    CHECKLIST_ITEMS_REPATRIATION,
    CHECKLIST_ITEMS_SWEDEN,
    FUNERAL_STATUSES,
    MEMORIAL_DAYS,
    FuneralCase,
    FuneralTrackerPort,
    build_checklist,
    calculate_price,
    checklist_progress,
)
from app.ports.grant_tracker import GrantApplication, GrantTrackerPort
from app.ports.translation import TranslationPort


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
    funerals: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    try:
        pending = intake.list_pending(session.token)
    except ClientError:
        pending = []

    # Count upcoming grant deadlines (<60 days)
    grants_upcoming = 0
    try:
        for g in _load_grant_database():
            color = _deadline_color(g.get("next_deadline", ""))
            if color in ("red", "yellow"):
                grants_upcoming += 1
    except Exception:
        pass

    # Count active funeral cases
    active_funerals = 0
    try:
        all_cases = funerals.list_cases(session.church_id)
        active_funerals = sum(1 for c in all_cases if c.status not in ("closed",))
    except Exception:
        pass

    return TEMPLATES.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "session": session,
            "pending_count": len(pending),
            "grants_upcoming": grants_upcoming,
            "active_funerals": active_funerals,
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


# --------------------------------------------------------------- content editor


def _flatten_content(content: dict, prefix: str = "") -> list[dict]:
    """Flatten a bilingual content dict into a list of editable rows.

    Each row has: key, sv, am.  Only leaf bilingual objects (dicts with "sv")
    are included.  Arrays like upcoming/announcements get indexed keys.
    """
    rows: list[dict] = []
    for k, v in content.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            if "sv" in v and isinstance(v.get("sv"), str):
                rows.append({
                    "key": full_key,
                    "sv": v.get("sv", ""),
                    "am": v.get("am", ""),
                })
            else:
                rows.extend(_flatten_content(v, full_key))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    rows.extend(_flatten_content(item, f"{full_key}[{i}]"))
    return rows


def _set_nested(content: dict, key: str, lang: str, value: str) -> None:
    """Set a value in a nested dict using a dot-notation key with optional array indices."""
    import re
    parts = re.split(r'\.', key)
    obj = content
    for i, part in enumerate(parts):
        # Check for array index like "upcoming[0]"
        match = re.match(r'^(\w+)\[(\d+)\]$', part)
        if match:
            arr_key = match.group(1)
            idx = int(match.group(2))
            if arr_key not in obj or not isinstance(obj[arr_key], list):
                return
            if idx >= len(obj[arr_key]):
                return
            if i == len(parts) - 1:
                if isinstance(obj[arr_key][idx], dict):
                    obj[arr_key][idx][lang] = value
                return
            obj = obj[arr_key][idx]
        else:
            if i == len(parts) - 1:
                if isinstance(obj.get(part), dict) and "sv" in obj[part]:
                    obj[part][lang] = value
                return
            if part not in obj or not isinstance(obj[part], dict):
                return
            obj = obj[part]


@router.get("/content-editor", response_class=HTMLResponse)
def content_editor(
    request: Request,
    flash: str | None = None,
    level: str = "success",
    store: ContentStorePort = Depends(get_content_store),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    content = store.load()
    rows = _flatten_content(content)

    return TEMPLATES.TemplateResponse(
        request=request,
        name="content_editor.html",
        context={
            "session": session,
            "rows": rows,
            "upcoming": content.get("upcoming", []),
            "flash": flash,
            "level": level,
        },
    )


@router.post("/content-editor/save")
async def content_editor_save(
    request: Request,
    store: ContentStorePort = Depends(get_content_store),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    form = await request.form()

    content = store.load()

    for form_key, value in form.items():
        # Form keys like "sv::church.name" or "am::church.name"
        if "::" not in form_key:
            continue
        lang, content_key = form_key.split("::", 1)
        if lang in ("sv", "am"):
            _set_nested(content, content_key, lang, str(value))

    store.save(content)

    return _flash_redirect("/content-editor", "Innehåll sparat", level="success")


@router.post("/content-editor/translate")
async def content_editor_translate(
    request: Request,
    translator: TranslationPort = Depends(get_translator),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    body = await request.json()
    text = body.get("text", "")
    target_lang = body.get("target_lang", "am")
    source_lang = body.get("source_lang", "sv")

    translated = translator.translate(text, source_lang, target_lang)

    from fastapi.responses import JSONResponse

    return JSONResponse({"translated": translated})


@router.get("/content-editor/add-activity", response_class=HTMLResponse)
def content_add_activity_form(
    request: Request,
    flash: str | None = None,
    level: str = "success",
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    return TEMPLATES.TemplateResponse(
        request=request,
        name="content_add_activity.html",
        context={
            "session": session,
            "today": date.today().isoformat(),
            "flash": flash,
            "level": level,
        },
    )


@router.post("/content-editor/add-activity")
def content_add_activity_save(
    request: Request,
    title_sv: str = Form(...),
    activity_date: str = Form(...),
    activity_time: str = Form(...),
    description_sv: str = Form(...),
    store: ContentStorePort = Depends(get_content_store),
    translator: TranslationPort = Depends(get_translator),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    title_am = translator.translate(title_sv, "sv", "am")
    description_am = translator.translate(description_sv, "sv", "am")

    content = store.load()
    if "upcoming" not in content:
        content["upcoming"] = []

    content["upcoming"].append({
        "title": {"sv": title_sv, "am": title_am},
        "date": activity_date,
        "time": activity_time,
        "description": {"sv": description_sv, "am": description_am},
    })

    store.save(content)

    return _flash_redirect(
        "/content-editor",
        f"Aktivitet tillagd: {title_sv}",
        level="success",
    )


# ---------------------------------------------------------------- audit reports


@router.get("/audit", response_class=HTMLResponse)
def audit_dashboard(request: Request):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    return TEMPLATES.TemplateResponse(
        request=request,
        name="audit_dashboard.html",
        context={"session": session},
    )


@router.post("/audit/generate/{report_type}", response_class=HTMLResponse)
def generate_audit_report(
    report_type: str,
    request: Request,
    activity: ActivityClientPort = Depends(get_activity_client),
    reporting: ReportingClientPort = Depends(get_reporting_client),
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
):
    """Generate a one-click audit report for a specific authority."""
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    today = date.today()
    year_start = f"{today.year}-01-01"
    year_end = today.isoformat()

    kpi_data = None
    error_message = None
    try:
        aggregates = activity.export_period(session.token, year_start, year_end)
        activities_payload = [asdict(a) for a in aggregates]
        total_participants = sum(a.get("participants_total", 0) for a in activities_payload)
        total_activities = len(activities_payload)
        by_type: dict[str, int] = {}
        by_age: dict[str, int] = {}
        for a in activities_payload:
            by_type[a["activity_type"]] = by_type.get(a["activity_type"], 0) + a.get("participants_total", 0)
            for band, n in a.get("age_band_counts", {}).items():
                by_age[band] = by_age.get(band, 0) + n
        kpi_data = {
            "period": f"{today.year}",
            "total_activities": total_activities,
            "total_participants": total_participants,
            "by_type": by_type,
            "by_age_band": by_age,
        }
    except ClientError as exc:
        error_message = f"Kunde inte hämta KPI-data: {exc}"

    grants = tracker.list_applications(session.church_id)
    grant_summary = {
        "total": len(grants),
        "submitted": sum(1 for g in grants if g.status == "submitted"),
        "approved": sum(1 for g in grants if g.status == "approved"),
        "rejected": sum(1 for g in grants if g.status == "rejected"),
    }

    return TEMPLATES.TemplateResponse(
        request=request,
        name="audit_report.html",
        context={
            "session": session,
            "report_type": report_type,
            "kpi": kpi_data,
            "grants": grant_summary,
            "error_message": error_message,
            "generated_at": today.isoformat(),
            "church_name": "Abune Tekle Haymanot Etiopiska Ortodoxa Tewahedo Kyrkan",
            "org_number": "802492-9237",
        },
    )


# ------------------------------------------------------------------- funerals


@router.get("/funerals", response_class=HTMLResponse)
def funerals_list(
    request: Request,
    flash: str | None = None,
    level: str = "success",
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    cases = tracker.list_cases(session.church_id)
    cases.sort(key=lambda c: c.created_at or datetime.min, reverse=True)

    return TEMPLATES.TemplateResponse(
        request=request,
        name="funerals_list.html",
        context={
            "session": session,
            "cases": cases,
            "flash": flash,
            "level": level,
        },
    )


@router.get("/funerals/new", response_class=HTMLResponse)
def funeral_new_form(
    request: Request,
    flash: str | None = None,
    level: str = "success",
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    return TEMPLATES.TemplateResponse(
        request=request,
        name="funeral_new.html",
        context={
            "session": session,
            "today": date.today().isoformat(),
            "flash": flash,
            "level": level,
        },
    )


@router.post("/funerals/new")
def funeral_create(
    request: Request,
    background_tasks: BackgroundTasks,
    deceased_name: str = Form(...),
    deceased_name_am: str = Form(""),
    date_of_death: str = Form(...),
    date_of_birth: str = Form(""),
    contact_person: str = Form(...),
    contact_phone: str = Form(""),
    package: str = Form("standard"),
    repatriation: str | None = Form(None),
    repatriation_destination: str = Form("ethiopia"),
    eder_name: str = Form(""),
    eder_contribution: float = Form(0.0),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    is_repatriation = repatriation == "on"
    pkg_price, rep_price, total = calculate_price(package, is_repatriation)

    import uuid
    case_id = f"f-{uuid.uuid4().hex[:8]}"

    case = FuneralCase(
        case_id=case_id,
        church_id=session.church_id,
        status="registered",
        created_at=datetime.utcnow(),
        deceased_name=deceased_name,
        deceased_name_am=deceased_name_am,
        date_of_death=date_of_death,
        date_of_birth=date_of_birth,
        contact_person=contact_person,
        contact_phone=contact_phone,
        package=package,
        repatriation=is_repatriation,
        repatriation_destination=repatriation_destination if is_repatriation else "",
        eder_name=eder_name,
        eder_contribution=eder_contribution,
        package_price=pkg_price,
        repatriation_price=rep_price,
        total_price=total,
        checklist=build_checklist(is_repatriation),
    )

    tracker.save_case(case)
    background_tasks.add_task(_dispatch_funeral_webhook, case)

    return _flash_redirect(
        f"/funerals/{case_id}",
        f"Ärende registrerat: {deceased_name}",
        level="success",
    )


@router.get("/funerals/{case_id}", response_class=HTMLResponse)
def funeral_detail(
    case_id: str,
    request: Request,
    flash: str | None = None,
    level: str = "success",
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    case = tracker.get_case(session.church_id, case_id)
    if case is None:
        return _flash_redirect("/funerals", "Ärendet hittades inte", level="error")

    done, total = checklist_progress(case.checklist)

    checklist_items_doc = [(k, l) for k, l in CHECKLIST_ITEMS_SWEDEN if k.startswith("doc_")]
    checklist_items_log = [(k, l) for k, l in CHECKLIST_ITEMS_SWEDEN if k.startswith("log_")]
    checklist_items_cer = [(k, l) for k, l in CHECKLIST_ITEMS_SWEDEN if k.startswith("cer_")]
    checklist_items_aft = [(k, l) for k, l in CHECKLIST_ITEMS_SWEDEN if k.startswith("aft_")]

    memorial_dates = []
    if case.date_of_death:
        try:
            dod = date.fromisoformat(case.date_of_death)
            from datetime import timedelta
            memorial_dates = [(dod + timedelta(days=d)).isoformat() for d, _, _ in MEMORIAL_DAYS]
        except ValueError:
            pass

    return TEMPLATES.TemplateResponse(
        request=request,
        name="funeral_detail.html",
        context={
            "session": session,
            "case": case,
            "done": done,
            "total": total,
            "statuses": FUNERAL_STATUSES,
            "checklist_items_doc": checklist_items_doc,
            "checklist_items_log": checklist_items_log,
            "checklist_items_cer": checklist_items_cer,
            "checklist_items_aft": checklist_items_aft,
            "checklist_items_rep": CHECKLIST_ITEMS_REPATRIATION,
            "memorial_days": MEMORIAL_DAYS,
            "memorial_dates": memorial_dates,
            "flash": flash,
            "level": level,
        },
    )


@router.post("/funerals/{case_id}/status")
def funeral_status_update(
    case_id: str,
    request: Request,
    status: str = Form(...),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    case = tracker.get_case(session.church_id, case_id)
    if case is None:
        return _flash_redirect("/funerals", "Ärendet hittades inte", level="error")

    if status in FUNERAL_STATUSES:
        case.status = status
        tracker.save_case(case)

    return _flash_redirect(f"/funerals/{case_id}", f"Status: {status}", level="success")


@router.post("/funerals/{case_id}/checklist")
async def funeral_checklist_update(
    case_id: str,
    request: Request,
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    case = tracker.get_case(session.church_id, case_id)
    if case is None:
        return _flash_redirect("/funerals", "Ärendet hittades inte", level="error")

    form = await request.form()
    for key in case.checklist:
        case.checklist[key] = key in form

    tracker.save_case(case)

    return _flash_redirect(f"/funerals/{case_id}", "Checklista uppdaterad", level="success")


@router.post("/funerals/{case_id}/notes")
def funeral_notes_update(
    case_id: str,
    request: Request,
    notes: str = Form(""),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    case = tracker.get_case(session.church_id, case_id)
    if case is None:
        return _flash_redirect("/funerals", "Ärendet hittades inte", level="error")

    case.notes = notes
    tracker.save_case(case)

    return _flash_redirect(f"/funerals/{case_id}", "Anteckningar sparade", level="success")


@router.post("/funerals/{case_id}/memorial")
def funeral_memorial_save(
    case_id: str,
    request: Request,
    memorial_text_sv: str = Form(""),
    memorial_text_am: str = Form(""),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    case = tracker.get_case(session.church_id, case_id)
    if case is None:
        return _flash_redirect("/funerals", "Ärendet hittades inte", level="error")

    case.memorial_text_sv = memorial_text_sv
    case.memorial_text_am = memorial_text_am
    tracker.save_case(case)

    return _flash_redirect(f"/funerals/{case_id}", "Minnestext sparad", level="success")


# ---------------------------------------------------------- funeral memorial page


@router.get("/funerals/{case_id}/memorial-page", response_class=HTMLResponse)
def funeral_memorial_page(
    case_id: str,
    request: Request,
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
):
    session = _require_session(request)
    if isinstance(session, RedirectResponse):
        return session

    case = tracker.get_case(session.church_id, case_id)
    if case is None:
        return _flash_redirect("/funerals", "Ärendet hittades inte", level="error")

    memorial_dates = []
    if case.date_of_death:
        try:
            dod = date.fromisoformat(case.date_of_death)
            from datetime import timedelta
            memorial_dates = [(dod + timedelta(days=d)).isoformat() for d, _, _ in MEMORIAL_DAYS]
        except ValueError:
            pass

    return TEMPLATES.TemplateResponse(
        request=request,
        name="funeral_memorial.html",
        context={
            "case": case,
            "memorial_days": MEMORIAL_DAYS,
            "memorial_dates": memorial_dates,
        },
    )


# ---------------------------------------------------------- funeral JSON API (n8n)

_FUNERAL_API_PII_BLOCKED = {
    "contact_person", "contact_phone", "contact_email",
    "date_of_birth", "notes", "eder_contribution",
}


@router.get("/api/funerals")
def funeral_api(
    request: Request,
    grief_calendar_active: str | None = None,
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
    settings: Settings = Depends(get_settings),
):
    token = request.headers.get("X-API-Token", "")
    expected = getattr(settings, "funeral_api_token", "") or os.environ.get("FUNERAL_API_TOKEN", "test-funeral-api-token")
    if not token or token != expected:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    cases = tracker.list_cases("c1")

    if grief_calendar_active == "true":
        cases = [c for c in cases if c.grief_calendar_active]

    result = []
    for c in cases:
        entry = {
            "case_id": c.case_id,
            "church_id": c.church_id,
            "status": c.status,
            "deceased_name": c.deceased_name,
            "deceased_name_am": c.deceased_name_am,
            "date_of_death": c.date_of_death,
            "package": c.package,
            "repatriation": c.repatriation,
            "repatriation_destination": c.repatriation_destination,
            "grief_calendar_active": c.grief_calendar_active,
            "ceremony_date": c.ceremony_date,
        }
        result.append(entry)

    from fastapi.responses import JSONResponse
    return JSONResponse(result)


# ---------------------------------------------------------- funeral webhook dispatch

import os
import logging

logger = logging.getLogger("admin-web.funeral")


def _dispatch_funeral_webhook(case: FuneralCase) -> None:
    webhook_url = os.environ.get("N8N_WEBHOOK_FUNERAL_CASE", "")
    if not webhook_url:
        logger.info("N8N_WEBHOOK_FUNERAL_CASE not set, skipping dispatch")
        return
    try:
        import httpx
        payload = {
            "case_id": case.case_id,
            "church_id": case.church_id,
            "deceased_name": case.deceased_name,
            "package": case.package,
            "date_of_death": case.date_of_death,
            "repatriation": case.repatriation,
            "repatriation_destination": case.repatriation_destination,
        }
        httpx.post(webhook_url, json=payload, timeout=5.0)
    except Exception as exc:
        logger.warning("Funeral webhook dispatch failed: %s", exc)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
