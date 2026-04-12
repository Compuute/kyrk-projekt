"""Session port — abstracts how a session cookie is validated.

MVP: FakeSessionAdapter parses `user_id:church_id:role` from the cookie.
Production: JWTSessionAdapter validates a real PropelAuth JWT and
extracts the same three fields (user_id, org_id, role).

The port pattern lets the route code call `session_port.validate(cookie)`
without knowing *how* the cookie was created or what crypto is involved.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SessionInfo:
    token: str
    user_id: str
    church_id: str
    role: str


class SessionPort(Protocol):
    def validate(self, cookie_value: str | None) -> SessionInfo | None:
        """Return a SessionInfo if the cookie is valid, None otherwise.

        Must NOT raise on invalid input — return None and let the caller
        decide whether to redirect to /login or return 401.
        """
        ...
