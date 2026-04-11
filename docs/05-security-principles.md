# 05 — Security Principles

## Core principles

1. **Security by design** — threat-model first, implement second.
2. **Least privilege** — one service account per Cloud Run service; minimal IAM scopes.
3. **Defense in depth** — auth at edge, RBAC in service, validation in model, audit in log.
4. **Zero trust between zones** — RED, YELLOW, GREEN never share a service account or bucket.
5. **Fail loudly** — reject on ambiguity; do not silently strip fields.
6. **Encrypt what matters** — field-level encryption for identity fields at rest.
7. **Audit everything that writes** — admin actions on RED data produce audit events.

## Concrete rules

- No secrets in code or env files in git. All secrets via GCP Secret Manager.
- All API endpoints use Pydantic models for input validation.
- All endpoints return typed errors with proper HTTP status codes (400/401/403/404/409/422/500).
- All RED endpoints require PropelAuth authentication.
- All write operations on RED data check RBAC role.
- All access to identity fields emits an audit event (`who`, `when`, `what`, `why`).
- No public search endpoints. Verification endpoints return only what is strictly necessary.
- Rate limiting on all public endpoints (membership-intake, certificate verification).

## Testing

- TDD-first: write the failing test, then the minimal implementation.
- Security-relevant tests must cover:
  - unauthorized access returns 401
  - insufficient role returns 403
  - malformed input returns 422
  - audit events are emitted on writes

## Threat model reference

See [`architecture/threat-model.md`](architecture/threat-model.md) for the STRIDE walkthrough.
