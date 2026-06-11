"""Zitadel OIDC-backed authentication adapter.

Reads ONLY the claims the service actually needs:
- user_id (sub)
- organization id (urn:zitadel:iam:org:id claim, treated as church_id)
- role within the project (urn:zitadel:iam:org:project:roles claim)
"""
from __future__ import annotations

import jwt
from app.domain.errors import NotAuthorized
from app.domain.models import Actor, Role


class ZitadelAuthAdapter:
    def __init__(self, issuer_url: str, client_id: str) -> None:
        self._issuer_url = issuer_url.rstrip("/")
        self._client_id = client_id
        # Lazy load JWK client
        self._jwks_client = None

    def _get_jwks_client(self) -> jwt.PyJWKClient:
        if self._jwks_client is None:
            jwks_url = f"{self._issuer_url}/oauth/v2/keys"
            # No custom ssl_context: PyJWKClient uses the system trust store and
            # verifies the issuer's TLS certificate + hostname. This fetch is the
            # trust anchor for every authenticated request, so verification must
            # never be disabled. These adapters run only in production (factory
            # wires FakeAuthAdapter otherwise), so there is no dev case for a bypass.
            self._jwks_client = jwt.PyJWKClient(jwks_url)
        return self._jwks_client

    def authenticate(self, token: str) -> Actor:
        if not token:
            raise NotAuthorized("missing token")

        try:
            jwks_client = self._get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=self._issuer_url,
                options={
                    "require": ["sub", "iss", "exp"],
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except Exception as exc:
            raise NotAuthorized("invalid token") from exc

        user_id = payload.get("sub", "")
        church_id = payload.get("urn:zitadel:iam:org:id", "")
        
        # Extract role from project roles claim
        roles_claim = payload.get("urn:zitadel:iam:org:project:roles", {})
        assigned_role = None

        # Fallback for church_id if missing from standard claim: extract it from roles_claim
        if not church_id and roles_claim:
            for role_name, val in roles_claim.items():
                if role_name in {"admin", "pastor", "editor", "viewer"}:
                    if isinstance(val, dict):
                        for k, v in val.items():
                            if k.isdigit():
                                church_id = k
                                break
                            elif isinstance(v, list):
                                for item in v:
                                    if str(item).isdigit():
                                        church_id = str(item)
                                        break
                                if church_id:
                                    break
                if church_id:
                    break

        # Look for matching role scoped to the user's church organization
        for role_name, val in roles_claim.items():
            if role_name in {"admin", "pastor", "editor", "viewer"}:
                if isinstance(val, dict):
                    if church_id in val:
                        assigned_role = role_name
                        break
                    for proj_id, org_ids in val.items():
                        if church_id == proj_id:
                            assigned_role = role_name
                            break
                        if isinstance(org_ids, list) and church_id in org_ids:
                            assigned_role = role_name
                            break
                if assigned_role:
                    break

        if not assigned_role:
            for role_name in roles_claim:
                if role_name in {"admin", "pastor", "editor", "viewer"}:
                    assigned_role = role_name
                    break

        if not user_id or not church_id or not assigned_role:
            raise NotAuthorized("user missing required OIDC claims")

        try:
            role = Role(assigned_role)
        except ValueError as exc:
            raise NotAuthorized("unknown role") from exc

        return Actor(
            user_id=user_id,
            church_id=church_id,
            role=role,
        )
