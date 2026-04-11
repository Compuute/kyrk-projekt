# 02 — Sovereignty

## Principle

Swedish church data stays in the EU, under Swedish law, and under the church's
operational control. No third-country data flows. No hidden dependencies.

## Data residency

- Primary region: `europe-north1` (Finland)
- Fallback region: `europe-west1` (Belgium)
- Firestore, Cloud Storage, BigQuery all provisioned in EU multi-region or EU single-region
- No US-region fallbacks are configured

## Vendor considerations

| Vendor | Role | Notes |
|---|---|---|
| Google Cloud | Hosting | EU regions only; DPA signed |
| Anthropic API | LLM calls (via n8n) | Aggregated data only; no PII; zero-retention where possible |
| PropelAuth | RBAC / sessions | EU data region where supported; no PII beyond email in PropelAuth |
| Fortnox | Accounting integration | Aggregates only; no member linkage |

## Risk rules

- Any new vendor must be reviewed against this doc before integration.
- Any cross-border data flow requires written approval + DPIA update.
- Secrets are stored only in GCP Secret Manager (never in code or env files checked in).

## Exit plan

- All data is exportable as JSON / CSV at any time.
- Firestore collections map cleanly to service boundaries.
- Terraform describes every provisioned resource — reproducible in another EU cloud if needed.
