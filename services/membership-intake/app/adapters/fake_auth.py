from __future__ import annotations

from app.domain.errors import NotAuthorized
from app.domain.models import Actor, Role


class FakeAuthAdapter:
    """Test/dev auth adapter. Tokens have the form `user_id:church_id:role`."""

    def authenticate(self, token: str) -> Actor:
        if not token or token.count(":") != 2:
            raise NotAuthorized("invalid token")
        user_id, church_id, role_str = token.split(":")
        try:
            role = Role(role_str)
        except ValueError as exc:
            raise NotAuthorized(f"unknown role: {role_str}") from exc
        return Actor(user_id=user_id, church_id=church_id, role=role)
