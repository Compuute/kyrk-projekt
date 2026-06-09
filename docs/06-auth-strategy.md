# 06 — Auth Strategy

## MVP: PropelAuth

> [!NOTE]
> **Planned Migration**: PropelAuth is designated to be replaced by **Zitadel Cloud** (SaaS) in Phase 3 to eliminate GDPR/FISA sovereignty risks associated with US-based cloud infrastructure. See [ADR-016](14-architecture-decisions.md) and the backlog issue.
>
> For the initial MVP, we use [PropelAuth](https://www.propelauth.com/) for multi-tenant RBAC via the `propelauth-fastapi` library.


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
| YELLOW write (ingest from background task) | service account, not user |
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

## Phase 3: Zitadel Cloud (SaaS) Migration

To address the GDPR and FISA sovereignty risks of using a US-based provider (PropelAuth) for handling user identity and access details, we will migrate authentication and multi-tenant RBAC to **Zitadel Cloud**.

### Why Zitadel Cloud

- **Swiss-Hosted SaaS**: Zitadel is a Swiss company offering hosting in Switzerland/EU, providing full compliance with EU data sovereignty standards and no risk from US FISA/Cloud Act search warrants.
- **Zero Ops Overhead**: Fully managed SaaS model, avoiding the database (PostgreSQL), server, patching, and scaling overhead of self-hosting Keycloak.
- **Native Multi-Tenancy**: Zitadel "Organizations" map perfectly to our church multi-tenancy model.
- **Standardized Tokens**: Replaces the proprietary `propelauth-fastapi` SDK with standard JWT token verification via JWKS (e.g. using `pyjwt` or `authlib`), preventing vendor lock-in.
- **Drop-in Adapter Swap**: Using the hexagonal architecture, the change is entirely isolated to replacing `PropelAuthAdapter` with a new `ZitadelAuthAdapter` implementing `AuthPort`.

## Security model summary


- All RED endpoints require authentication.
- YELLOW read endpoints require at least `viewer`.
- GREEN: public (wifi portal) or admin (review queues).
- No API keys in code — everything via Secret Manager.
- Service accounts are per-service (least privilege).
