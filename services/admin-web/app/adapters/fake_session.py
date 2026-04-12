"""Fake session adapter for MVP and tests.

The cookie value is the raw bearer token in `user_id:church_id:role` form.
Implements the SessionPort protocol so route code uses `session_port.validate()`
without knowing that the cookie format is fake.
"""
from __future__ import annotations

from app.ports.session import SessionInfo


class FakeSessionAdapter:
    """Trivial session adapter — parses `user:church:role` tokens."""

    def validate(self, cookie_value: str | None) -> SessionInfo | None:
        if not cookie_value or cookie_value.count(":") != 2:
            return None
        user_id, church_id, role = cookie_value.split(":")
        if role not in {"admin", "pastor", "secretary", "viewer"}:
            return None
        return SessionInfo(
            token=cookie_value,
            user_id=user_id,
            church_id=church_id,
            role=role,
        )


# Backwards-compatible alias used by routes.py until all call sites
# switch to the port-based pattern.
def parse_session_cookie(value: str | None) -> SessionInfo | None:
    return FakeSessionAdapter().validate(value)
