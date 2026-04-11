# Policies

## Data retention

| Data | Retention |
|---|---|
| Pending intake (never approved) | 30 days, then deleted |
| Active membership records | Until explicit deletion request |
| Certificates | Until explicit revocation |
| Audit logs | 2 years |
| Aggregated KPI reports | 7 years |
| OpenClaw pending reviews | 90 days |

## Deletion requests

- Member-initiated deletion requests are handled by admin within 30 days.
- Deletion removes RED data; aggregates in YELLOW are retained (no individual linkage).
- Certificates are revoked (not deleted) to preserve verification integrity.

## Access reviews

- Quarterly: admin reviews the list of users per church and role.
- Annually: full policy review and DPIA update.

## Incident handling

- Any suspected PII leak to the LLM triggers the OpenClaw incident runbook (see `04-ai-boundaries.md`).
- Any suspected unauthorized RED access triggers an audit log review within 24 hours.
