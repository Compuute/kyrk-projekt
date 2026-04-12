# Incident logs

Every time something surprising happens in production (or a close call
in dev), write a short incident log here. The goal is not blame — the
goal is that the next person who reads it learns something.

## When to write one

- Any page (on-call alert fired)
- Any rollback
- Any failed deploy that wasn't a flaky test
- Any suspected PII / security event (write it *immediately*, even if
  you're still triaging)
- Any "that was close" near-miss worth capturing

If in doubt, write it. It's five minutes.

## How to write one

1. Copy [`TEMPLATE.md`](TEMPLATE.md) to
   `YYYY-MM-DD-short-slug.md` (lowercase, dashes, no spaces).
2. Fill in every section. It's fine to leave `TODO(followup)` bullets.
3. Open a PR. Reviewers check that the facts line up with logs, not
   that the prose is pretty.
4. Merge. Don't wait for the root cause to be "finished" — incremental
   updates are better than a perfect retrospective that never lands.

## Template-driven sections

The template has the same shape as the prompts in
[`docs/13-runbook.md`](../docs/13-runbook.md): summary, timeline,
root cause, impact, what worked, what didn't, follow-ups. Keep it
short. A page of text is usually plenty.

## What the files here are

| File | Purpose |
|---|---|
| [`TEMPLATE.md`](TEMPLATE.md) | The blank template |
| `2025-03-14-firestore-latency-spike.md` | Training example: transient infrastructure latency surfaced as user-visible 500s |
| `2025-04-02-deploy-iam-role-binding-drift.md` | Training example: deploy failed because an IAM binding was removed out-of-band |

Both training examples are **fictional** — they show the shape a
real incident log should have, and each teaches a specific lesson
worth carrying forward. Treat them as the "definition of done" for
your own incident logs.

## What is NOT stored here

- Raw payloads from PII incidents — **never** check in any field that
  was flagged. Reference only hashes, run IDs, and counts.
- Credentials, tokens, keys — rotate them, don't document them.
- Personal names of reporters or affected users — use roles (admin,
  pastor, the reporter) and `church_id`.
