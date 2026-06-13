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
| Zitadel Cloud | RBAC / sessions (OIDC) | EU/CH region where supported; no PII beyond email. ⚠️ Currently on the US region (free tier) with synthetic data only — migrates to EU/CH before production (see ADR-017). |
| Fortnox | Accounting integration | Aggregates only; no member linkage |

> ⚠️ **Current-state deviation:** the authentication service (Zitadel) runs
> temporarily on the US region during the build-out phase, with test/synthetic
> data only. This is a deliberate, time-boxed deviation — see ADR-017. No real
> personal data enters the US instance, and it is migrated to an EU/CH region
> before production. The data plane (Firestore, GCS, BigQuery) stays in
> `europe-north1` as stated above.

## Risk rules

- Any new vendor must be reviewed against this doc before integration.
- Any cross-border data flow requires written approval + DPIA update.
- Secrets are stored only in GCP Secret Manager (never in code or env files checked in).

## Exit plan

- All data is exportable as JSON / CSV at any time.
- Firestore collections map cleanly to service boundaries.
- Terraform describes every provisioned resource — reproducible in another EU cloud if needed.
