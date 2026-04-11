# Prompt redlines

## OpenClaw MAY see

- Activity counts and aggregates
- Participant totals and age-band counts
- Finance aggregates (revenue buckets, cost buckets)
- KPI and ROI numbers
- Funding tags (e.g. `arvsfonden`)
- Period strings (e.g. `2025-Q2`)
- Strategy documents, impact blueprints (GREEN)
- Public marketing copy (GREEN)

## OpenClaw must NEVER see

- Names (first_name, last_name, full_name)
- Personnummer / SSN
- Phone numbers, emails, addresses
- Certificate IDs associated with individuals
- member_id, submission_id, user_id (internal identifiers that re-identify)
- Raw Firestore documents from RED collections
- Anything that has not been aggregated via `reporting-service`

## How violations are detected

1. **reporting-service** validates ingress and rejects forbidden fields
   with a 422 (`app/domain/pii_guard.py`).
2. **n8n sanitizer** runs before every HTTP call to Anthropic, using
   profiles defined in `sanitizer/profiles.json`.
3. **Template system prompt** explicitly tells the model to return an
   error if it believes it has received personal data.
4. **Response validator** enforces the template's `expected_output_schema`
   so unexpected fields fail the run.

## Incident response

If a sanitizer violation fires:

1. n8n aborts the workflow (the API call never happens).
2. The offending payload is hashed and logged; the raw payload is discarded.
3. Admin is alerted via `ADMIN_NOTIFY_WEBHOOK`.
4. A postmortem is required before the workflow is re-enabled.
5. Root-causing must identify how the field slipped past `reporting-service`
   — that is the defense-in-depth failure that matters.

If it turns out a payload was actually sent to Anthropic with PII:

1. Document what was sent, when, and the run ID.
2. Request data deletion from Anthropic per contract (zero-retention is
   configured by default for our tenant).
3. DPIA update.
4. Notify affected individuals if the risk assessment requires it.
