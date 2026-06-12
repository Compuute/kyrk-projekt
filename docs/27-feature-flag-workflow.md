# 27 — Feature-Flag Workflow (how we ship safely at scale)

How we use feature flags so a change can reach 300k users **without** a bad
release hitting everyone at once — and without slowing developers down. This is
the day-to-day workflow; the rollout *mechanism* is in
[`docs/15` → Release-safety layer](15-ab-testing-strategy.md).

## The principle (what Netflix, Google, betting platforms all do)

**Deploy ≠ release.** Code is merged and deployed continuously, but a risky
change ships *dark* (off) and is turned on for a growing % of users separately.
This decouples "the code is in production" from "users see it", which is what
makes high-frequency shipping safe. Flags are not a nice-to-have at scale —
they are the unit of release.

Three things are automated so this does not become a burden:

| Automation | What it does | Where |
|---|---|---|
| **Risk advisor** | Reads each PR's diff; if it touches high-blast-radius code without a flag, posts a (non-blocking) comment suggesting one | `.github/workflows/flag-advisor.yml` |
| **Hygiene gate** | Every flag must have owner + type + description; release/experiment flags must expire; an **expired flag fails CI** (forces cleanup) | `tests/test_flags_hygiene.js` (in `make test`) |
| **Runtime control** | Ramp % and kill switch live in KV → change takes effect with **no redeploy** | `functions/_middleware.ts` + KV `feature_flags` |

The human decides whether to flag; the tooling enforces discipline and surfaces
risk. That is the balance — automated governance, not automated gating.

## Does this change need a flag? (decision guide)

The advisor nudges you, but the rule of thumb:

**Flag it when** the change is behaviour-affecting AND high blast-radius:
- edge middleware (`functions/`), auth/payment adapters, API routes
- user-facing pages (`frontend/member-portal/src/pages/`), the donation/intake flows
- data-model or schema changes
- anything you would be nervous to ship to all 300k at 2am

**Skip the flag** for low-risk, no-behaviour-change work:
- docs, tests, cosmetic CSS (e.g. the nav-dropdown fix), refactors with no
  behaviour change, dependency bumps

When unsure, flag it — a flag costs ~3 lines and an expiry date; a bad release
costs trust.

## Flag types & lifecycle

| Type | Lifespan | Expires? | Example |
|---|---|---|---|
| `release` | short — gates a rollout, then **deleted** | **yes** | new funeral layout |
| `experiment` | duration of an A/B test (Phase 3) | **yes** | intake field order |
| `ops` | long-lived kill switch / circuit breaker | optional | disable AI-summary on incident |
| `permission` | entitlement by segment | optional | beta features for pilot churches |

`release` and `experiment` flags are **tech debt by design** — they must die.
The hygiene gate enforces this: a release flag with no `expires`, or one past
its `expires`, fails CI until you remove it (and the now-permanent code).

## How to work with a flag

**1. Add it** to [`frontend/member-portal/flags.json`](../frontend/member-portal/flags.json):
```json
"new-funeral-layout": {
  "enabled": true, "rollout": 0,
  "type": "release", "owner": "<you>",
  "created": "<today>", "expires": "<+4-8 weeks>",
  "description": "New funeral page layout"
}
```

**2. Gate the code** (edge-evaluated; snippet in `docs/15`):
```js
if (flags["new-funeral-layout"]) { /* new path */ } else { /* old path */ }
```

**3. Ramp it** via KV (no redeploy): `0 → 5 → 25 → 50 → 100`, watching error
rate / Pages Functions logs between steps (the read-only observability in the
KYA layer is what you watch). Trouble → set `enabled:false` → safe next request
(within KV's seconds-to-~60s propagation window — see `docs/15`).

**4. Retire it** once at 100% and stable: delete the flag from `flags.json`,
delete the `else` branch and the `if`. The hygiene gate's `expires` date is your
deadline — when it passes, CI nags until the flag is gone.

## Anti-patterns (what NOT to do)

- **Letting flags pile up.** The #1 real-world failure. That is why `expires` is
  mandatory and enforced — a graveyard of stale flags is worse than no flags.
- **Putting variant/flag state in a tracking cookie or anything PII-linked.**
  Our bucket is a non-PII `ab` integer; it is a *functional* cookie and is
  disclosed like `selected_language` (privacy-by-design — see `docs/15`).
- **Nesting flags** (a flag inside a flag inside a flag). Keep them flat and
  short-lived.
- **Flagging trivial changes.** Cosmetic/no-behaviour work ships directly; the
  advisor already excludes docs/tests/CSS so it will not nag you.
- **Long-lived `release` flags.** If it needs to live forever it is an `ops`
  flag, not a release flag — label it correctly.

## Phasing (ties to our ADRs)

- **Now:** release flags + progressive rollout for *safety* (this doc + `docs/15`
  Release-safety layer). No experiments yet.
- **Phase 3** (>500 MAU + metrics pipeline, per ADR-009 / `docs/15`): reuse the
  same edge-bucket mechanism for real A/B *experiments*, and evaluate GrowthBook
  when test volume justifies it.
