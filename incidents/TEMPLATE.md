# YYYY-MM-DD — <short slug>

**Severity:** page / office hours / log-only
**Services affected:** membership-service, …
**Zone(s):** RED / YELLOW / GREEN / Infra
**Authors:** <name or role>
**Incident commander:** <name or role>

## Summary

One paragraph. What happened, in plain language. Somebody who wasn't
there should understand the shape of the problem in under a minute.

## Timeline

All times in UTC unless noted.

- `HH:MM` — alert fired / first noticed
- `HH:MM` — first responder acknowledged
- `HH:MM` — rollback / mitigation applied
- `HH:MM` — user-visible impact ended
- `HH:MM` — root cause understood
- `HH:MM` — long-term fix deployed
- `HH:MM` — incident closed

## Root cause

The actual technical reason — not the first thing you noticed, not
the alert message, the *why*. If you don't know yet, say so and file
a follow-up.

## Impact

- **Users affected:** e.g. "all admins in 2 churches", "anonymous
  traffic to /intake"
- **Data affected:** e.g. "no data loss", "3 audit events double-
  written", "unknown until Firestore export is re-indexed"
- **Duration of user-visible impact:** e.g. "14 minutes (14:22–14:36)"
- **Financial / reputational:** e.g. "none", "one failed intake
  submission had to be retried manually"

## What worked

- ...
- ...

## What didn't

- ...
- ...

## Follow-ups

Each follow-up has an owner, an action, and a due date. File them as
GitHub issues if they outlive this incident.

- [ ] <owner> — <action> — <due>
- [ ] <owner> — <action> — <due>

## References

- Cloud Run revision: `<service>-00042-xyz`
- Commit SHA: `<sha>`
- Log query: `gcloud logging read '…' …`
- Related runbook: [`docs/13-runbook.md#<section>`](../docs/13-runbook.md)
- Related PR: owner/repo#123
