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
| `services/membership-intake` | RED | Public intake form (pending status) |
| `services/membership-service` | RED | Member lifecycle, RBAC, audit |
| `services/certificate-service` | RED | Digital certificates + privacy-preserving verification |
| `services/activity-service` | YELLOW | Activity tracking (aggregated counts only) |
| `services/reporting-service` | YELLOW | KPI / ROI reports, OpenClaw input |

## Frontend

| Module | Zone | Stack |
|---|---|---|
| `frontend/mobile-web` | mixed | (future) admin/member portal |
| `frontend/wifi-intake-portal` | GREEN | static HTML + vanilla JS |

## Automation

- `automation/n8n` — workflow definitions (self-hosted on Cloud Run)
- `automation/openclaw` — prompt templates + sanitizer profiles (Anthropic API via n8n)

## Infra

- `infra/terraform` — GCP baseline (Cloud Run, Firestore, GCS, Secret Manager, IAM, BigQuery)

## Docs

Start with [`docs/00-vision.md`](docs/00-vision.md), [`docs/01-architecture-red-yellow-green.md`](docs/01-architecture-red-yellow-green.md), and [`docs/ai-context.md`](docs/ai-context.md).

## Auth

MVP uses **PropelAuth** for multi-tenant RBAC. BankID is an interface/stub for Phase 2. See [`docs/06-auth-strategy.md`](docs/06-auth-strategy.md).
