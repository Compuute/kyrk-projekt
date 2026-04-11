"""PropelAuth adapter for membership-intake admin endpoints.

Reads ONLY user_id, church_id (= PropelAuth org id), and role.
No email, no profile. If the service doesn't use the field, it should
not load it.
"""
from __future__ import annotations

from app.domain.errors import NotAuthorized
from app.domain.models import Actor, Role


class PropelAuthAdapter:
    def __init__(self, auth_url: str, api_key: str) -> None:
        self._auth_url = auth_url
        self._api_key = api_key
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from propelauth_fastapi import init_auth  # pragma: no cover

            self._client = init_auth(self._auth_url, self._api_key)
        return self._client

    def authenticate(self, token: str) -> Actor:
        if not token:
            raise NotAuthorized("missing token")
        client = self._ensure_client()
        try:
            user = client.validate_access_token_and_get_user(
                authorization_header=f"Bearer {token}"
            )
        except Exception as exc:  # pragma: no cover
            raise NotAuthorized("invalid token") from exc

        orgs = getattr(user, "org_id_to_org_member_info", None) or {}
        first = next(iter(orgs.values()), None)
        if first is None:
            raise NotAuthorized("user has no organization membership")
        try:
            role = Role(getattr(first, "assigned_role", None))
        except ValueError as exc:
            raise NotAuthorized("unknown role") from exc
        return Actor(
            user_id=user.user_id,
            church_id=getattr(first, "org_id", ""),
            role=role,
        )
