# kyrk-projekt

Modular, secure, mobile-first church platform on Google Cloud Platform.

## Architecture zones

- **RED** — sensitive identity, membership, certificates (encrypted, no public search)
- **YELLOW** — aggregates only, KPI, reporting, ROI
- **GREEN** — strategy, content, AI (OpenClaw), impact, Wi-Fi portal

## Principles

- Security by design
- Sovereignty by design
- GDPR (Sweden)
- Data minimization (spårminimering)
- Human-in-the-loop for all AI outputs
- TDD-first, mobile-first, modular, multi-tenant (`church_id`)
- Low cost (nonprofit context)

## Services

| Service | Zone | Purpose |
|---|---|---|
| `services/membership-intake` | RED | Public intake form + admin approval flow |
| `services/membership-service` | RED | Member lifecycle, RBAC, audit |
| `services/certificate-service` | RED | Digital certificates + privacy-preserving verification |
| `services/activity-service` | YELLOW | Activity tracking (aggregated counts only) |
| `services/reporting-service` | YELLOW | KPI / ROI reports, OpenClaw input |
| `services/admin-web` | mixed | Server-rendered admin UI (HTML, no frameworks) |

Each service ships a `Dockerfile`, runs as a non-root user, and exposes
`/healthz`. Each service has two adapter modes selected by `ADAPTER_MODE`:
`memory` (default, in-process) for tests and local dev, `production`
(Firestore + KMS + PropelAuth + BigQuery) for Cloud Run.

## Frontend

| Module | Zone | Stack |
|---|---|---|
| `frontend/wifi-intake-portal` | GREEN | static HTML + vanilla JS |
| `frontend/mobile-web` | mixed | placeholder for a future React/native client |

The day-to-day admin UI lives in `services/admin-web` — see above.

## Automation

- `automation/n8n` — workflow definitions (self-hosted on Cloud Run)
- `automation/openclaw` — prompt templates + sanitizer profiles (Anthropic API via n8n)

## Infra

- `infra/terraform` — GCP baseline (Cloud Run, Firestore, GCS, Secret Manager, IAM, BigQuery)

## CI / CD

Two GitHub Actions workflows live at the repo root in
[`.github/workflows/`](../.github/workflows/):

- `ci.yml` — runs pytest across all services, the wifi-portal Node tests,
  syntax-check, and `terraform validate` on every push and PR. No secrets,
  no GCP access.
- `deploy.yml` — manual workflow that builds container images, pushes
  them to Artifact Registry, and deploys to Cloud Run via Workload
  Identity Federation (no static GCP keys in GitHub). See the README in
  the workflows folder for the one-time GCP setup.

## Docs

Start with [`docs/00-vision.md`](docs/00-vision.md), [`docs/01-architecture-red-yellow-green.md`](docs/01-architecture-red-yellow-green.md), and [`docs/ai-context.md`](docs/ai-context.md).

## Auth

MVP uses **PropelAuth** for multi-tenant RBAC. BankID is an interface/stub for Phase 2. See [`docs/06-auth-strategy.md`](docs/06-auth-strategy.md).
