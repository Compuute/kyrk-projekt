"""PropelAuth-backed authentication adapter.

Reads ONLY the three claims the service actually needs:
- user_id
- organization id (treated as church_id)
- role within that organization

Does not pull email, profile, or any other field. The principle is
"just because we can store or expose it, doesn't mean we should" —
if the service doesn't use the field, it should not load it.

IAM: the service account needs no GCP permissions for PropelAuth.
Access to PropelAuth itself is via API key stored in Secret Manager
and passed in via env at startup.
"""
from __future__ import annotations

from app.domain.errors import NotAuthorized
from app.domain.models import Actor, Role


class PropelAuthAdapter:
    def __init__(self, auth_url: str, api_key: str) -> None:
        self._auth_url = auth_url
        self._api_key = api_key
        self._client = None  # lazy

    def _ensure_client(self):
        if self._client is None:
            # Lazy import so tests that never instantiate this adapter
            # don't require propelauth-fastapi to be installed.
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
        except Exception as exc:  # pragma: no cover — network / lib errors
            raise NotAuthorized("invalid token") from exc

        # Extract ONLY what we need. No email, no profile, nothing else.
        org = _first_org(user)
        if org is None:
            raise NotAuthorized("user has no organization membership")
        try:
            role = Role(org["role"])
        except (KeyError, ValueError) as exc:
            raise NotAuthorized("unknown role") from exc
        return Actor(
            user_id=user.user_id,
            church_id=org["org_id"],
            role=role,
        )


def _first_org(user) -> dict | None:
    """Return the first org the user belongs to, or None.

    Multi-church users are out of scope for MVP. When support is needed,
    the API will require an explicit church_id header so the service can
    pick the right org without guessing.
    """
    orgs = getattr(user, "org_id_to_org_member_info", None)
    if not orgs:
        return None
    first = next(iter(orgs.values()))
    return {
        "org_id": getattr(first, "org_id", None),
        "role": getattr(first, "assigned_role", None),
    }
