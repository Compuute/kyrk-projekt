# membership-intake

Public intake flow. A person scans a QR code at the church, fills a minimal
form on their phone, and lands as a `pending` submission. A human admin
reviews and approves before the record becomes a real member in
`membership-service`.

## Zone

**RED** on storage (submissions contain identity data) but the *submission*
endpoint is public. No read endpoints are exposed publicly.

## Design

- Single public POST endpoint: `/intake`
- Rate limited (per IP + per church)
- Captures minimal fields only:
  - first_name, last_name, phone, email, personal_number
  - church_id
  - gdpr_consent (bool)
  - consent_timestamp (ISO 8601)
- GDPR consent is required — rejected otherwise.
- Submission is stored with status `pending`.
- A webhook fires to notify the admin (n8n-compatible).
- BankID integration is interface-only for MVP.

## Running

```bash
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Handoff to membership-service

When an admin approves a pending submission (separate flow in
`membership-service`), the fields from this service are used to create the
real member. This service does NOT write to `membership-service`; it only
stores pending submissions and fires a notification. The admin approval is
where the RED handoff happens.

## Rate limiting

A simple token-bucket limiter is implemented in-memory for MVP. Production
should swap it for a Redis-backed limiter.

## Security

- No auth required to submit (by design — public flow).
- Rate limited per IP and per church to prevent abuse.
- All submissions emit a `submission_received` audit event for traceability.
- No GET endpoints exposed to the public.
