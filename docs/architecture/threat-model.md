# Threat model (STRIDE)

Lightweight STRIDE walkthrough for MVP. Revisit before Phase 2.

## Assets

1. Member identity data (RED)
2. Certificates and their verification chain (RED)
3. Aggregated KPI / ROI data (YELLOW)
4. OpenClaw outputs and Wi-Fi content (GREEN)
5. Admin credentials (PropelAuth sessions)

## Trust boundaries

- Public internet → membership-intake, wifi-intake-portal, certificate verification
- Admin user → PropelAuth → RED services
- n8n → reporting-service (service account)
- n8n → Anthropic API (sanitizer enforced)

## STRIDE per asset

### Member identity data (RED)

| Threat | Mitigation |
|---|---|
| **S**poofing | PropelAuth sessions + verified JWT |
| **T**ampering | Pydantic validation, Firestore rules, audit events |
| **R**epudiation | Audit log per write |
| **I**nformation disclosure | Field-level encryption, no public search, least-privilege IAM |
| **D**enial of service | Rate limiting on public endpoints, Cloud Run concurrency caps |
| **E**levation of privilege | RBAC enforced in FastAPI dependency, per-church scoping |

### Certificates (RED)

| Threat | Mitigation |
|---|---|
| Spoofing (fake cert) | UUID cert_id, verification signature, status check |
| Information disclosure via verification | Verification returns only type/date/church/status — no identity |
| Tampering | Immutable issuance, revocation is a status change not a delete |

### Aggregated data (YELLOW)

| Threat | Mitigation |
|---|---|
| PII smuggling via YELLOW ingest | reporting-service rejects any payload with `name`, `personal_number`, `email`, `phone` |
| Over-aggregation leak | Age bands and counts are min-cell checked before export |

### OpenClaw / LLM (GREEN)

| Threat | Mitigation |
|---|---|
| Prompt injection leaking aggregates | System prompt hardening + structured JSON output |
| LLM hallucinating facts into board reports | Human-in-the-loop review before use |
| PII leak to Anthropic | Sanitizer whitelist + ingest validation |

## Residual risks (accepted for MVP)

- Admin account compromise → mitigated by PropelAuth MFA (enforced) but not eliminated
- n8n self-hosted availability → mitigated by Cloud Run + health checks, not by HA
- Anthropic API outage → graceful n8n failure, no data loss (retry next cron)
