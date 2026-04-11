# 01 — Architecture: RED / YELLOW / GREEN

The platform uses three data zones with strict flow rules.

## RED — sensitive identity

**Contents**
- Member identities, personal_number, contact details
- Membership status, history, notes
- Certificates (baptism, confirmation, etc.)
- Audit logs of admin actions

**Rules**
- Field-level encryption on identity fields
- All endpoints require authentication (PropelAuth)
- RBAC enforced (admin, pastor, secretary, viewer)
- No public search endpoints
- No bulk export without admin approval
- All access is logged

**Services**
- `membership-intake` (write-only, pending status)
- `membership-service`
- `certificate-service`

## YELLOW — aggregates only

**Contents**
- Activity counts, attendance totals, age-band breakdowns
- Finance aggregates (revenue, cost buckets)
- KPI and ROI metrics

**Rules**
- No personal identifiers ever (validated on ingress)
- Safe for internal reporting and grant applications
- Safe to send to OpenClaw sanitizer → Anthropic API

**Services**
- `activity-service`
- `reporting-service`

## GREEN — strategy, content, public

**Contents**
- OpenClaw prompt templates and outputs
- Wi-Fi portal content
- Impact blueprints, strategy docs
- Public marketing copy

**Rules**
- No RED data ever
- Reviewed by humans before publication
- AI outputs are pending until an admin approves

**Modules**
- `automation/openclaw`
- `frontend/wifi-intake-portal`
- `docs/impact/*`

## Flow rules

```
RED ──(aggregation only, sanitizer-enforced)──► YELLOW ──(sanitizer)──► GREEN/LLM
```

- RED → YELLOW is one-way, through explicit aggregation code.
- YELLOW → GREEN passes through the sanitizer (see `automation/openclaw/sanitizer`).
- GREEN → RED is **forbidden**. AI outputs never modify member data directly; an admin manually applies decisions.

## Enforcement

- Sanitizer profiles (`automation/openclaw/sanitizer/profiles.json`) validate payloads by whitelist.
- `reporting-service` rejects any payload containing `personal_number`, `name`, `email`, or `phone`.
- CI linting (future) can scan for forbidden field names in GREEN code paths.
