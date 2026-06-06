"""Shared helpers for all route modules."""
from __future__ import annotations

from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request, status
from pathlib import Path

from app.api.deps import get_session_adapter
from app.ports.session import SessionInfo


def _templates() -> Jinja2Templates:
    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    return Jinja2Templates(directory=str(templates_dir))


TEMPLATES = _templates()


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
