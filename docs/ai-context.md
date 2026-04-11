# AI Context

Paste this block at the start of every Claude Code session.

```
Project: kyrk-projekt

Platform:
- GCP
- Cloud Run
- Firestore
- BigQuery
- Cloud Storage
- n8n (self-hosted on Cloud Run)
- OpenClaw (prompt templates → Anthropic API via n8n)

Architecture:
- RED = sensitive identity, membership, certificates (encrypted, no public search)
- YELLOW = aggregates only, KPI, reporting, ROI
- GREEN = strategy, content, AI, impact, Wi-Fi portal

Principles:
- Security by design
- Sovereignty by design
- GDPR Sweden
- Spårminimering (data minimization)
- Human-in-the-loop (all AI outputs reviewed before use)
- TDD-first
- Mobile-first
- Modular
- Reusable across churches (multi-tenant via church_id)
- Low cost (nonprofit context)

Auth strategy (MVP):
- PropelAuth for multi-tenant RBAC (FastAPI library)
- BankID as interface/stub for future integration
- No custom auth implementation

OpenClaw production flow:
- n8n triggers scheduled workflows
- n8n fetches aggregated data from reporting-service (YELLOW only)
- n8n calls Anthropic API with OpenClaw prompt template + data
- API returns structured JSON (response_format: json)
- n8n stores result for human review
- Admin approves before any output is published or acted on
- Sanitizer runs BEFORE data reaches LLM (enforced in n8n)
```
