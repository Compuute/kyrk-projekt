"""Zitadel Session adapter for production.

Validates the session cookie as a standard Zitadel OIDC token.
"""
from __future__ import annotations

import jwt
from app.ports.session import SessionInfo


class JWTSessionAdapter:
    def __init__(self, issuer_url: str, client_id: str, client_secret: str = "", redirect_uri: str = "") -> None:
        self._issuer_url = issuer_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._jwks_client = None

    def _get_jwks_client(self) -> jwt.PyJWKClient:
        if self._jwks_client is None:
            jwks_url = f"{self._issuer_url}/oauth/v2/keys"
            
            # Create a default context that bypasses certificate verification for local/dev environments
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self._jwks_client = jwt.PyJWKClient(jwks_url, ssl_context=ssl_context)
        return self._jwks_client

    def validate(self, cookie_value: str | None) -> SessionInfo | None:
        if not cookie_value:
            return None
        try:
            jwks_client = self._get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(cookie_value)
            payload = jwt.decode(
                cookie_value,
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
        except Exception:
            # Invalid or expired token — reject silently.
            return None

        user_id = payload.get("sub", "")
        church_id = payload.get("urn:zitadel:iam:org:id", "")
        
        # Extract role
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
            return None

        return SessionInfo(
            token=cookie_value,
            user_id=user_id,
            church_id=church_id,
            role=assigned_role,
        )

    def exchange_code(self, code: str) -> str:
        import httpx
        token_url = f"{self._issuer_url}/oauth/v2/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        r = httpx.post(token_url, data=data, timeout=10.0)
        r.raise_for_status()
        token_data = r.json()
        token = token_data.get("id_token") or token_data.get("access_token")
        if not token:
            raise RuntimeError("No token returned from Zitadel")
        return token
