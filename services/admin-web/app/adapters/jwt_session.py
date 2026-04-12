"""PropelAuth JWT session adapter for production.

Validates the session cookie as a JWT signed by the PropelAuth tenant.
Extracts only user_id, org_id (= church_id), and role — nothing else.

Dependencies are lazy-imported so tests using FakeSessionAdapter never
need PyJWT or cryptography installed.

Required env vars:
- PROPELAUTH_VERIFIER_KEY   the RS256 public key (PEM) from PropelAuth
- PROPELAUTH_ISSUER         the tenant issuer URL

Both are loaded once at __init__; rotate by restarting the service
after updating Secret Manager.
"""
from __future__ import annotations

from app.ports.session import SessionInfo


class JWTSessionAdapter:
    def __init__(self, verifier_key: str, issuer: str) -> None:
        self._verifier_key = verifier_key
        self._issuer = issuer

    def validate(self, cookie_value: str | None) -> SessionInfo | None:
        if not cookie_value:
            return None
        try:
            import jwt  # PyJWT — lazy import

            payload = jwt.decode(
                cookie_value,
                self._verifier_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={
                    "require": ["sub", "iss", "exp"],
                    "verify_exp": True,
                    "verify_iss": True,
                },
            )
        except Exception:
            # Invalid, expired, or tampered token — reject silently.
            # Never log the cookie value — it may contain PII-adjacent
            # material (session id, email hint, etc.).
            return None

        user_id = payload.get("sub", "")
        orgs = payload.get("org_id_to_org_member_info", {})
        if not orgs:
            return None
        # MVP assumes one org per user. Multi-org selection is Phase 2.
        first_key = next(iter(orgs))
        org = orgs[first_key]
        church_id = org.get("org_id", first_key)
        role = org.get("assigned_role", "")
        if role not in {"admin", "pastor", "secretary", "viewer"}:
            return None

        return SessionInfo(
            token=cookie_value,
            user_id=user_id,
            church_id=church_id,
            role=role,
        )
