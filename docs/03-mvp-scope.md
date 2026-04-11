# 03 — MVP Scope

## In scope

### Services
- `membership-intake` — public pending registration
- `membership-service` — member lifecycle + RBAC + audit
- `certificate-service` — digital baptism certificates + privacy-preserving verification
- `activity-service` — aggregated activity tracking
- `reporting-service` — KPI / ROI reports, OpenClaw input

### Frontend
- `wifi-intake-portal` — static site, content pushed via n8n

### Automation
- `n8n` workflows:
  - new pending membership notification
  - monthly KPI export
  - quarterly OpenClaw analysis
  - Fortnox aggregate reporting
  - Wi-Fi portal content update
- `openclaw` prompt templates (quarterly variance, annual planning, ROI prioritization, content planning)
- Sanitizer profiles (YELLOW-only, GREEN-only)

### Infra
- Terraform baseline (Cloud Run, Firestore, GCS, Secret Manager, IAM, BigQuery, n8n Cloud Run)

### Auth
- PropelAuth FastAPI integration
- BankID as interface/stub

## Out of scope (for MVP)

- Custom auth implementation
- Member-facing mobile app (native)
- Full Fortnox bi-directional sync
- Native BankID integration
- BigQuery analytics dashboards
- Public member directory
- Payment processing
- SMS notifications
- GraphQL API

## Definition of done for MVP

- All five services scaffolded with tests, Pydantic models, and in-memory adapters
- PropelAuth integration on RED services
- n8n workflows defined as JSON with documented triggers
- OpenClaw prompts defined with JSON schemas and sanitizer references
- Terraform applies cleanly in a test GCP project
- Docs cover architecture, sovereignty, AI boundaries, auth, security
