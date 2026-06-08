# 03 — MVP Scope

## In scope

### Services
- `membership-intake` — public pending registration (individual 200 kr/mån, family 500 kr/mån)
- `membership-service` — member lifecycle + RBAC + audit + payment ports (autogiro, Swish, tezkar)
- `certificate-service` — digital baptism certificates + privacy-preserving verification
- `reporting-service` — KPI / ROI reports, bank loan reports (PaymentSummary)
- `admin-web` — dashboard, intake approval, certificates, grants, funerals, tax consent

### Frontend
- `member-portal` — static site on Cloudflare Pages (vanilla HTML, 0 dependencies)
  - Registration with membership type (enskild/familj) + Swish first payment
  - Donation page with Swish deep links
  - Bilingual (Swedish + Amharic)
  - Dynamic per-church config via content.json

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

- Custom auth implementation (PropelAuth handles it)
- Member-facing mobile app (native) — PWA covers this
- Full Fortnox bi-directional sync
- Native BankID integration (Bankgirot e-medgivande handles autogiro signing)
- BigQuery analytics dashboards
- Public member directory
- SMS notifications
- GraphQL API
- Astro migration (evaluated and deferred — vanilla HTML meets all requirements)
- AI-animated educational content (architecture prepared, content production later)

## Definition of done for MVP

- All five services scaffolded with tests, Pydantic models, and in-memory adapters
- PropelAuth integration on RED services
- Terraform applies cleanly in GCP project `kyrk-projekt` (europe-north1)
- Frontend live on Cloudflare Pages (kyrka-portal.pages.dev)
- Registration form end-to-end: form → API → Swish payment → autogiro
- Payment module: ports for autogiro (Billecta), Swish, tezkar, bank reports
- Dynamic per-church config (content.json) supporting 10 churches
- 75+ guard tests + 51 frontend functional tests + 66 intake tests + 28 payment tests
- Docs cover architecture, sovereignty, AI boundaries, auth, security, payments
