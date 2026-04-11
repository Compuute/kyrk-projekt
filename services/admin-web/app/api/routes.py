"""HTML routes. Each route either renders a template or redirects."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.adapters.fake_session import SessionInfo, parse_session_cookie
from app.api.deps import (
    get_certificate_client,
    get_intake_client,
    get_settings,
)
from app.config import Settings
from app.ports.client_errors import ClientError
from app.ports.clients import (
    CertificateClientPort,
    IntakeClientPort,
    IssueCertificateRequest,
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
    info = parse_session_cookie(cookie)
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


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
