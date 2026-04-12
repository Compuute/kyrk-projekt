# 15 — A/B Testing Strategy

## Status: NOT NOW — planned for Phase 3

A/B testing is not in MVP and not in Phase 2. Here's why, when it
makes sense, and exactly how to introduce it when the time comes.

## Why not now

Four prerequisites must all be true before A/B testing adds value.
Today, none of them are:

| Prerequisite | Status (MVP) | When it flips |
|---|---|---|
| **Enough traffic** to reach statistical significance | <5 churches, ~50 users | >20 churches OR >500 monthly active users |
| **Product metrics pipeline** that captures the outcome variable | No analytics beyond BigQuery KPI aggregates | When we add event-level tracking (e.g. "intake completion rate") |
| **Feature velocity** high enough that you're releasing alternatives | One deployment cadence, one version for all | When the team is >2 devs and shipping weekly |
| **Someone who interprets results** — a product owner or data person | No product analytics role | When the board hires one or a volunteer steps up |

Running A/B tests without these four just adds routing complexity and
produces numbers nobody acts on.

## Trigger criteria — "start building A/B infrastructure when..."

**All three of these are true simultaneously:**

1. You have >500 monthly active users across >10 churches (enough
   traffic for a two-week test with 80% power at α=0.05 on a
   10-percentage-point MDE on a 50% baseline conversion rate).
2. You have an event-level analytics pipeline (not just monthly
   aggregates) that can answer "how many people completed intake
   this week?" or "how many pastors opened the KPI dashboard?"
3. You have a person (or a defined role) who will read the test
   results and make ship/kill decisions within 2 weeks of test
   completion.

If even one of these is missing, A/B testing will produce data that
nobody uses — which is worse than not testing at all, because you'll
still pay the complexity cost.

## What to A/B test first (when you're ready)

In order of expected impact and ease of measurement:

### 1. Wi-Fi portal content variants

**What:** different welcome messages, CTA copy, or tile ordering on
the static portal.
**Why first:** it's the highest-traffic surface (every Wi-Fi guest
sees it), and the outcome is easy to measure ("Bli medlem" tile
click-through → intake POST received).
**How:** extend the `content-config.json` schema with an `ab` key
that defines two variant configs. The `content.js` decision logic
picks variant A or B based on a hash of `Date.now()` bucketed into
two groups (50/50 split, no cookies, no tracking — the bucket is
time-based, not user-based, so there's no PII concern). Log the
variant as a query param on the "Bli medlem" link so
membership-intake can record which variant led to the submission.
**Zone:** GREEN → GREEN. No PII involved.

### 2. Intake form field order

**What:** swap the order of `first_name` + `last_name` vs
`phone` + `email` to see which reduces drop-off.
**Why:** intake completion rate is the most direct grant-relevant
metric ("how many people completed registration?").
**How:** membership-intake renders two form orderings. The variant
is a URL param set by the portal or by the admin-web intake link.
The intake-service records the variant in the submission metadata
(a new `variant` field on `IntakeSubmission`). Reporting-service
aggregates completion rate per variant.
**Zone:** RED (because intake holds identity data, but the variant
field itself is YELLOW-safe — it's just `"A"` or `"B"`).

### 3. KPI dashboard presentation

**What:** show the same data with two different card layouts or
metric orderings to see which prompts more admin action (e.g.
clicking "Generera" a second time, or navigating to intake after
seeing low numbers).
**Why:** if the dashboard doesn't drive action, it's decoration.
**How:** admin-web renders two templates (same data, different
layout). Variant selection is based on the session's user_id hash
so the same admin sees a consistent experience. Event tracking
records "dashboard viewed" + "action taken within 5 minutes."
**Zone:** mixed — no PII in the test itself, but requires admin-web
event logging which is a new pipeline.

## Architecture — how A/B fits into the platform

### Option A: GrowthBook (recommended)

[GrowthBook](https://www.growthbook.io/) is open-source and can be
self-hosted. It provides:

- Feature flags with percentage rollouts
- A/B experiment assignment with SDK-side bucketing
- Results analysis UI with Bayesian statistics
- BigQuery integration for metrics

Install: self-host on Cloud Run (same pattern as n8n). Cost: free.

### Option B: feature flags via a simple JSON config

If GrowthBook is too heavy for the team, the simplest version:

1. Add a `feature_flags.json` to Cloud Storage (same pattern as
   wifi portal content).
2. Each service reads the config at startup (or on a timer).
3. A flag looks like:
   ```json
   {
     "intake_form_order": {
       "enabled": true,
       "variants": ["name_first", "phone_first"],
       "weights": [50, 50],
       "bucketing": "time"  // or "user_id_hash"
     }
   }
   ```
4. A tiny helper function picks the variant per request.
5. The chosen variant is logged to BigQuery via reporting-service.

No SDK, no GrowthBook, no new infrastructure — just a JSON file
and a helper. Results analysis is manual SQL in BigQuery.

### What NOT to build

- Don't build a custom assignment engine with sticky sessions and
  server-side variant storage. That's what GrowthBook does and it
  took them years to get the statistics right.
- Don't track A/B variants in the session cookie — that's PII-adjacent
  and violates the wifi portal's "no cookies" pledge.
- Don't expose individual-level variant assignments outside the
  YELLOW zone. The aggregate "variant A had 62% completion, variant B
  had 58%" is YELLOW. The per-user assignment is borderline RED and
  should be treated as such.

## Privacy considerations

- **Wi-Fi portal:** variants are time-bucketed, not user-bucketed. No
  cookies, no fingerprinting, no localStorage. The user never knows
  they're in a test. GDPR Article 6(1)(f) — legitimate interest (UX
  improvement) likely applies; confirm with the DPO before launching.
- **Intake form:** the variant field is `"A"` or `"B"` — not PII.
  But it's stored alongside PII in the submission object. When the
  submission is redacted after approval, the variant field survives
  (it's useful for aggregate analysis). Ensure reporting-service
  treats it as YELLOW.
- **Admin UI:** user_id hash bucketing means the variant is
  deterministic per user. The hash is not stored — it's computed
  per request. No new PII is created.

## Timeline

| Phase | What | When |
|---|---|---|
| **MVP (now)** | No A/B. Ship one version. Measure via KPI dashboard. | 2025 |
| **Phase 2** | Add event-level tracking to BigQuery. Monitor intake completion rate + dashboard engagement. | When >10 churches |
| **Phase 3** | Introduce A/B testing for wifi portal content variants (Option B: simple JSON flags). | When trigger criteria are met |
| **Phase 4** | If the team grows and tests are frequent, evaluate GrowthBook (Option A). | When >2 tests/month |

## What to read next

- [`docs/14-architecture-decisions.md#ADR-009`](14-architecture-decisions.md) —
  the ADR recording this decision
- [`docs/04-ai-boundaries.md`](04-ai-boundaries.md) — relevant if you
  ever A/B test OpenClaw prompt variants (the sanitizer applies per
  variant, not globally)
- [`docs/governance/policies.md`](governance/policies.md) — retention
  rules for the variant field in intake submissions
