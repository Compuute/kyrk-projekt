# 2025-03-14 — firestore-latency-spike

**Severity:** office hours
**Services affected:** membership-service, certificate-service
**Zone(s):** RED
**Authors:** on-call engineer
**Incident commander:** on-call engineer

> NOTE: This is a **fictional training example**. It's here to show
> the shape a real incident log should have and to teach specific
> lessons. If a production incident with the same symptoms happens,
> write a fresh log in a new file — don't edit this one.

## Summary

Between 09:12 and 09:34 UTC, roughly 8% of requests to
`membership-service` returned 500s with `DEADLINE_EXCEEDED` from
the Firestore client. `certificate-service` was affected on a
smaller scale because it shares the same Firestore database. No
user data was lost; the failing requests were retried by operators
and the next-try success rate was 100%. Rollback was not needed —
Firestore latency returned to normal on its own.

## Timeline

- `09:12` — alert fired: e2e.yml healthz job failed, both RED
  services returned 503 intermittently
- `09:14` — on-call ack'd, opened Cloud Run logs
- `09:16` — confirmed that the containers were healthy and the
  errors were coming from the Firestore client (`DEADLINE_EXCEEDED`
  on `get` and `add` calls with 10s timeouts)
- `09:18` — checked the GCP Firestore status page → Firestore
  reported elevated latency in `eur3`
- `09:20` — decided NOT to roll back (rollback would not fix an
  upstream latency issue) and NOT to fail over (no fallback region
  is provisioned in MVP)
- `09:22` — posted a status update to the admin team channel:
  "Firestore elevated latency, monitoring, no action required"
- `09:34` — Firestore latency back to baseline, error rate dropped
  to 0
- `09:40` — incident closed

## Root cause

Upstream Firestore latency in the `eur3` multi-region. GCP reported
the incident on their status page within the same window. Our code
did not cause this and could not have prevented it.

The application-side consequence was amplified by:

1. A hard-coded 10-second timeout in the Firestore client. Any
   single operation slower than 10 s surfaced as a 500 to the user.
2. No retry-with-backoff on the Firestore client side. The first
   failed `get` became a user-visible 500 immediately.

## Impact

- **Users affected:** admins in three churches retried a total of
  ~14 member lookups manually; no end users saw the errors because
  the public intake endpoint uses a separate rate-limited path that
  didn't hit Firestore during the window (in-memory pending buffer
  was still serving fine)
- **Data affected:** none — no writes were lost, only reads timed out
- **Duration of user-visible impact:** 22 minutes (09:12–09:34)
- **Financial / reputational:** none

## What worked

- `/healthz` surfaced the degradation within 2 minutes via e2e.yml.
- The decision to NOT roll back was correct — rollback would have
  created noise without fixing anything.
- Audit events captured every admin retry with a clean actor trail,
  so we know exactly what operators did during the window.
- Cross-church 404 hiding was never invoked by any retry, so no
  accidental disclosure.

## What didn't

- No automatic client-side retry. Every transient blip became a
  user-visible 500 instead of a short pause.
- No status-page integration. The on-call had to manually check
  `status.cloud.google.com`. An automated ingest would have told
  us immediately this was upstream, not us.
- The Slack notification template for "Firestore degraded" doesn't
  exist, so the status update was ad-hoc.

## Follow-ups

- [ ] on-call team — add a `google.api_core.retry.Retry` wrapper
      around `get` / `add` calls in `FirestoreMemberRepository` and
      `FirestoreCertificateRepository` with exponential backoff
      (0.5 s → 4 s, max 4 attempts) — due: 2025-03-21
- [ ] ops — write a "upstream degraded" Slack template and link it
      from `docs/13-runbook.md#1-service-returning-5xx` — due: 2025-03-21
- [ ] devops — investigate subscribing the admin channel to GCP
      status page RSS so upstream incidents are auto-announced —
      due: 2025-04-01
- [ ] on-call team — add a regression test that asserts
      `FirestoreMemberRepository` retries on `DEADLINE_EXCEEDED`
      once the wrapper lands — due: 2025-03-21

## References

- Cloud Run revisions (unchanged during incident):
  `membership-service-00073-a1b`, `certificate-service-00041-c3d`
- GCP status: fictional incident `INC-XXX-XXX` — not a real ID
- Related runbook: [`docs/13-runbook.md#1-service-is-returning-5xx`](../docs/13-runbook.md)
- Related PRs: none yet (follow-ups pending)

---

## Lessons this example teaches

Every training incident log has a "lessons" footer so the reader
can extract the point quickly:

1. **Not every alert is your bug.** Upstream GCP latency can
   surface identically to a bad deploy. Check the status page
   before touching code.
2. **Rollback is not always the answer.** If the problem is
   upstream, rolling back adds noise and buys nothing.
3. **Client-side retries are part of the service.** A bare
   Firestore client is a landmine; wrap it with `api_core.retry`
   for anything on the hot path.
4. **`/healthz` is your first line of defense.** The fact that
   e2e.yml caught this in 2 minutes is why you don't skip healthz
   jobs to save compute.
5. **Write the status-update template BEFORE you need it.**
   Ad-hoc messages during an incident are fine; ad-hoc messages
   for the third time in a row are a gap.
