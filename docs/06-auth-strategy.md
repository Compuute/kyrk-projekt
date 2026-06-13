# 06 — Auth Strategy

> Hur kyrkorna hålls åtskilda (church_id = Zitadel-org) och hur en ny kyrka
> onboardas: [35-kyrko-multitenancy-och-onboarding.md](35-kyrko-multitenancy-och-onboarding.md).

Authentication and multi-tenant Role-Based Access Control (RBAC) are powered by **Zitadel Cloud (SaaS)**. Zitadel was chosen *to enable* 100% EU/Swiss data sovereignty and eliminate GDPR/FISA sovereignty risks (per [ADR-016](14-architecture-decisions.md)).

> ⚠️ **Current state — temporary deviation (see [ADR-017](14-architecture-decisions.md)).** The active instance runs on Zitadel's **free tier in the US region** (`kyrk-auth-oqvxjf.us1.zitadel.cloud`) while all auth functionality is being built and verified. **Data residency is therefore US, not EU/Swiss, right now — the sovereignty goal above is not yet met.** Hard gate: only test/synthetic data in this instance; the service must be moved to an EU/CH-region instance before any real personal data is entered or before public production. Nothing is deployed to production yet.

---

## Zitadel Cloud Integration

The system uses standard OpenID Connect (OIDC) and JSON Web Key Sets (JWKS) to authenticate users and verify access tokens locally in downstream services.

### Multi-Tenancy Mapping
- **Organization (Zitadel Org)**: Maps to a single local church (`church_id`). Each church owns its separate Zitadel organization.
- **Project Grants**: The primary organization (`EOTK Sverige`) defines the global `kyrk-portal` project and grants access to individual church organizations. This allows local church admins to manage their own users and roles autonomously.
- **Roles**:
  - `admin` — full RED read/write, can issue certificates, can approve AI outputs.
  - `pastor` — RED read/write within their church, can issue certificates.
  - `editor` — RED write for intake/update, no certificate issuance.
  - `viewer` — YELLOW read only (statistics, financial reports).
  - `teacher` — Sunday school only: for **own groups** (scoped by `teacher_user_ids`),
    record attendance and enroll children (enrollment requires guardian consent).
    **Cannot** create groups (staff only), and has **no** general RED member /
    certificate / funeral read or write. Sunday-school endpoints are hosted on
    `membership-service` (`routes_sunday_school.py`); all other RED endpoints
    reject `teacher` by explicit role check.

### Architecture & Verification
- **Frontend (`admin-web`)**: Handles standard OIDC authorization code flow. Directs unauthenticated users to Zitadel's login portal and exchanges the returned code for tokens via `/login/callback`. Token payload is stored in the secure HTTP-only `kyrk_session` cookie.
- **Downstream Services**: Receive the user's OIDC token as a bearer header. The adapter (`ZitadelAuthAdapter`) fetches the JWKS from Zitadel dynamically (`/oauth/v2/keys`) and verifies token authenticity and claims locally using RS256 signature verification.
- **Hexagonal Isolation**: Route handlers do not import vendor identity SDKs directly. The session and authentication details are abstracted behind a clean `SessionPort` and `AuthPort`, making tests fast and mockable.

---

## Endpoint RBAC Rules

| Zone | Role required | Allowed Roles |
|---|---|---|
| RED write | `admin`, `pastor`, or `editor` (scoped by endpoint) | `admin`, `pastor`, `editor` |
| RED read | `admin`, `pastor`, or `editor` | `admin`, `pastor`, `editor` |
| Certificate issue | `admin` or `pastor` | `admin`, `pastor` |
| Sunday school: attendance + enroll (own groups) | `teacher` or staff | `teacher`, `editor`, `pastor`, `admin` |
| Sunday school: create group | staff only | `admin`, `pastor`, `editor` |
| YELLOW read | `viewer` or higher | `admin`, `pastor`, `editor`, `viewer` |
| YELLOW write (ingest) | Service account role (e.g. backend tasks) | N/A (Internal) |
| GREEN public (wifi portal) | No auth | Public |
| GREEN admin (AI approve) | `admin` | `admin` |

---

## Troubleshooting & Verification

### Local Development Environment
To run the services locally in production authentication mode (`ADAPTER_MODE=production`), set the following environment variables:
- `ZITADEL_ISSUER_URL`: The instance issuer URL (e.g., `https://kyrk-auth-oqvxjf.us1.zitadel.cloud`)
- `ZITADEL_CLIENT_ID`: The OIDC application Client ID
- `ZITADEL_CLIENT_SECRET`: The application Client Secret (required for Basic authorization code exchange)
- `ZITADEL_REDIRECT_URI`: E.g., `http://localhost:8080/login/callback`

### Testing
All OIDC token validation code is tested locally using mock JWKS clients.
Run python unit tests:
```bash
source .venv/bin/activate
./scripts/local-ci.sh tests
```

---

## Phase 2: BankID

BankID acts as the identity verification layer for membership intake (verifying *who you are*), complementing Zitadel (which manages *what you can do*).
`services/membership-service` defines a `BankIdPort` interface, currently stubbed in dev mode, ready to be replaced with a real BankID provider client without altering core business logic.
