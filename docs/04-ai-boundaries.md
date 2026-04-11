# 04 — AI Boundaries

## What the AI (Anthropic API via OpenClaw/n8n) may see

- Activity counts and attendance aggregates (YELLOW)
- Age-band breakdowns (no individual ages)
- Finance aggregates (revenue/cost buckets)
- KPI / ROI numbers
- Strategy documents, impact blueprints (GREEN)
- Public marketing copy (GREEN)

## What the AI must NEVER see

- Names, personal_number, addresses
- Phone numbers, emails
- Certificate IDs linked to individuals
- Raw Firestore documents from RED collections
- Anything from the `membership-*` or `certificate-*` services that has not passed through aggregation

## Enforcement

1. **Sanitizer runs first.** `automation/openclaw/sanitizer/profiles.json` defines allowed fields per workflow.
2. **n8n enforces profile selection.** Each workflow declares its sanitizer profile; payloads are rejected if they fail validation.
3. **reporting-service rejects PII on ingest.** Any payload containing `personal_number`, `name`, `email`, or `phone` is rejected with a 422.
4. **Structured JSON output.** Prompts use `response_format: json` and declare their output schema. Free-form prose that could leak data is avoided.
5. **Human-in-the-loop.** All AI outputs land in a `pending_review` state. An admin approves before any downstream action.

## Incident response

If a sanitizer violation is detected:
1. The offending payload is logged (hash only — the payload itself is discarded).
2. The n8n workflow fails loudly and alerts the admin.
3. No data is sent to Anthropic.
4. Postmortem required before the workflow is re-enabled.

## Boundaries for prompts

Prompts must explicitly instruct the model:
- "You will never receive personal data. If you believe you have, stop and return `{\"error\": \"pii_detected\"}`."
- "Respond only in the declared JSON schema."
- "Do not request additional personal information."
