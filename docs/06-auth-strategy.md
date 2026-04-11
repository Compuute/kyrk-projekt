# 06 — Auth Strategy

## MVP: PropelAuth

We use [PropelAuth](https://www.propelauth.com/) for multi-tenant RBAC via the
`propelauth-fastapi` library.

### Why

- Multi-tenant out of the box: one PropelAuth "organization" == one church.
- RBAC out of the box: roles map cleanly to our admin / pastor / secretary / viewer model.
- FastAPI library is maintained and small.
- Free tier is sufficient for MVP workloads.
- No custom auth code — we avoid weeks of work and a large class of security bugs.

### Integration model

- `organization` in PropelAuth = one church (`church_id`).
- Users belong to one or more organizations with a role per organization.
- Roles:
  - `admin` — full RED read/write, can issue certificates, can approve AI outputs
  - `pastor` — RED read/write within their church, can issue certificates
  - `secretary` — RED write for intake/update, no certificate issuance
  - `viewer` — YELLOW read only (KPI, reports)

### FastAPI wiring

Each service initializes `propelauth-fastapi` once at startup and uses a
dependency for role checks. Services define an internal `AuthPort` interface
so the real PropelAuth client can be swapped for a fake in tests.

### Endpoint rules

| Zone | Role required |
|---|---|
| RED write | admin or pastor or secretary (scoped by endpoint) |
| RED read | admin, pastor, secretary |
| Certificate issue | admin or pastor |
| YELLOW read | viewer or higher |
| YELLOW write (ingest from n8n) | service account, not user |
| GREEN public (wifi portal) | no auth |
| GREEN admin (approve AI output) | admin |

### Secrets

- PropelAuth URL, API key, verifier key: stored in GCP Secret Manager.
- Loaded at service startup via ADC + Secret Manager client.

## Phase 2: BankID

BankID is planned for Phase 2 as the identity verification layer for
membership intake.

### Model

- BankID verifies *identity* (this is Anna Andersson, personnummer 19xx…).
- PropelAuth manages *sessions and roles* (Anna is an admin in Church A).
- They complement each other — BankID for who-you-are, PropelAuth for what-you-can-do.

### Interface now

`services/membership-service` already defines a `BankIdPort` interface with a
stub implementation. Phase 2 replaces the stub with a real BankID client
without changing any calling code.

## Security model summary

- All RED endpoints require authentication.
- YELLOW read endpoints require at least `viewer`.
- GREEN: public (wifi portal) or admin (review queues).
- No API keys in code — everything via Secret Manager.
- Service accounts are per-service (least privilege).
