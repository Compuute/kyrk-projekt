from __future__ import annotations

from app.domain.errors import NotAuthorized
from app.domain.models import Actor, Role


class FakeAuthAdapter:
    def authenticate(self, token: str) -> Actor:
        if not token:
            raise NotAuthorized("missing token")

        if token.count(":") == 2:
            user_id, church_id, role_str = token.split(":")
            try:
                role = Role(role_str)
            except ValueError as exc:
                raise NotAuthorized(f"unknown role: {role_str}") from exc
            return Actor(user_id=user_id, church_id=church_id, role=role)

        # Try decoding as an unverified JWT for local development/testing with real Zitadel
        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub", "")
            church_id = payload.get("urn:zitadel:iam:org:id", "")
            
            roles_claim = payload.get("urn:zitadel:iam:org:project:roles", {})
            assigned_role = None
            for role_name, projects in roles_claim.items():
                if role_name in {"admin", "pastor", "editor", "viewer"}:
                    for proj_id, org_ids in projects.items():
                        if church_id in org_ids:
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
                raise NotAuthorized("unverified JWT missing required claims")
                
            return Actor(user_id=user_id, church_id=church_id, role=Role(assigned_role))
        except Exception as exc:
            raise NotAuthorized("invalid token format") from exc
