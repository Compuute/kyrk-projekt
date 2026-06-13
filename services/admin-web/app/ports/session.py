"""Session port — abstracts how a session cookie is validated.

MVP: FakeSessionAdapter parses `user_id:church_id:role` from the cookie.
Production: JWTSessionAdapter validates a real Zitadel OIDC JWT and
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
    # Human-readable name for greetings. Falls back to user_id when the
    # token carries no name claim, so the UI never shows worse than today.
    display_name: str = ""

    @property
    def display(self) -> str:
        """Name to show in the UI — name claim if present, else the id."""
        return self.display_name or self.user_id


class SessionPort(Protocol):
    def validate(self, cookie_value: str | None) -> SessionInfo | None:
        """Return a SessionInfo if the cookie is valid, None otherwise.

        Must NOT raise on invalid input — return None and let the caller
        decide whether to redirect to /login or return 401.
        """
        ...

    def exchange_code(self, code: str) -> str:
        """Exchange the OIDC authorization code for an ID/Access token.

        May raise an exception if the exchange fails.
        """
        ...
