# 14 — Architecture Decision Records (ADRs)

Each decision below records **what** we chose, **why**, and
**when to revisit**. They're numbered by date, not by importance.

---

## ADR-001: Service-per-zone-boundary (originally six, now five)

**Date:** 2025-06
**Status:** amended by ADR-010 (activity+reporting merge)
**Context:** kyrk-projekt handles three sensitivity levels of data
(RED identity, YELLOW aggregates, GREEN content). A single monolith
would share a single service account, a single DB connection, and a
single deploy pipeline — making least-privilege impossible.
**Decision:** split into services along zone and trust boundaries.
The original prompt specified six; after 33 commits of empirical
data we consolidated to five by merging the two YELLOW services
(see ADR-010). The surviving boundaries are:
- membership-intake (RED, public)
- membership-service (RED, authenticated, KMS)
- certificate-service (RED, authenticated)
- reporting-service (YELLOW, authenticated, BigQuery)
- admin-web (UI, stateless)
**Consequence:** five services instead of six. Each service still has
its own SA, Firestore collections, IAM scope, Dockerfile, and test
suite. The operational overhead is reduced by one deploy job, one SA,
and ~350 lines of infrastructure code.
**When to revisit:** if a future requirement moves activity data into
RED (e.g., participant-level tracking with names), split them back.

---

## ADR-002: Plain HTML admin UI instead of React / SPA

**Date:** 2025-06
**Status:** accepted
**Context:** the admin UI needs to handle intake approval, certificate
issuance, and KPI viewing. These are form → submit → redirect flows
with no real-time interactivity.
**Decision:** server-rendered HTML via Jinja2 templates + plain CSS.
No JavaScript framework, no build pipeline, no CDN scripts. Same
design principle as the wifi-intake-portal.
**Consequence:** zero npm dependencies, zero build step, pages render
in <50 ms, auditable in a browser's "View Source". Downside: no inline
editing, no partial page updates without a full reload.
**When to revisit:** when a screen genuinely needs real-time feedback
(e.g. live participant counter during an event). At that point,
consider HTMX as progressive enhancement first, React only if HTMX
is insufficient.

---

## ADR-003: n8n for orchestration instead of a custom workflow engine

**Date:** 2025-06
**Status:** accepted
**Context:** the platform needs scheduled jobs (monthly KPI, quarterly
OpenClaw analysis, Fortnox sync, wifi portal content updates) and
webhook-triggered flows (new intake notification).
**Decision:** use self-hosted n8n on Cloud Run. Workflows are defined
as JSON and version-controlled in `automation/n8n/workflows/`.
**Consequence:** zero custom orchestration code, visual debugging in
the n8n UI, built-in retry logic. Downside: another Cloud Run service
to maintain (min 1 instance for cron reliability, ~€5-10/month).
**When to revisit:** if n8n's execution model becomes limiting (e.g.
complex fan-out with >100 parallel branches), evaluate Cloud Workflows
or Temporal.

---

## ADR-004: PropelAuth instead of custom auth

**Date:** 2025-06
**Status:** accepted
**Context:** building a secure multi-tenant RBAC system from scratch
takes weeks and introduces a large surface area for security bugs.
**Decision:** use PropelAuth for authentication + RBAC. Each church is
a PropelAuth organization; roles (admin/pastor/secretary/viewer) map to
PropelAuth org roles. Auth is a port — `FakeAuthAdapter` for tests,
`PropelAuthAdapter` for production.
**Consequence:** no session management code, no password hashing, no
token rotation logic. The free tier covers MVP. Downside: dependency
on a third-party SaaS for a critical path.
**When to revisit:** if PropelAuth pricing or availability becomes a
problem, swap the adapter for a self-hosted Keycloak or Auth0 — the
port interface stays the same.

---

## ADR-005: Adapter pattern with ADAPTER_MODE env var

**Date:** 2025-06
**Status:** accepted
**Context:** services need to run locally with no GCP credentials
(memory mode) AND in production with Firestore + KMS + PropelAuth
(production mode).
**Decision:** each service has a `factory.py` that reads `ADAPTER_MODE`
at startup and instantiates the right adapter set. Production adapters
lazy-import their GCP libraries so the test environment never needs
them installed.
**Consequence:** `make test` runs in <5 seconds with zero network
calls, every test uses in-memory adapters. Production swap is a single
env var.
**When to revisit:** if a third mode is needed (e.g. `staging` with
a different Firestore database), extend the factory. The pattern
itself is stable.

---

## ADR-006: Static wifi-intake-portal instead of React

**Date:** 2025-06
**Status:** accepted
**Context:** the Wi-Fi landing portal is shown to guests for ~2 seconds
on a captive portal. It must load instantly, use no cookies, no
tracking, no external scripts.
**Decision:** plain HTML + CSS + 80 lines of vanilla JS. Content
is loaded from a JSON file pushed to Cloud Storage by n8n.
**Consequence:** 7 KB total, renders on any device, passes any
privacy audit. Downside: adding a dynamic feature (e.g. a captive
portal registration form) would need more JS.
**When to revisit:** if the portal needs user-specific content
(e.g. personalized welcome after Wi-Fi login), evaluate whether a
simple form POST is sufficient before reaching for a framework.

---

## ADR-007: Structured JSON output for OpenClaw (no free-form prose)

**Date:** 2025-06
**Status:** accepted
**Context:** OpenClaw prompts call Anthropic API via n8n. Free-form
prose output is hard to validate, harder to audit, and risks leaking
data into unexpected fields.
**Decision:** every prompt template uses `response_format: json` and
declares an `expected_output_schema`. The n8n sanitizer validates the
response against the schema; invalid JSON aborts the run.
**Consequence:** AI outputs are machine-checkable, parseable, and
auditable. Human reviewers see structured data, not walls of text.
Downside: the AI cannot produce narrative reports directly — an admin
must compose narrative from the structured JSON if needed.
**When to revisit:** when the board requests a "narrative quarterly
report" format. At that point, add a second template with free-form
output but keep the structured template as the primary data source.

---

## ADR-008: CMEK for Firestore

**Date:** 2025-06
**Status:** accepted
**Context:** Google encrypts Firestore at rest by default, but with
Google-managed keys the data owner cannot revoke access at the
cryptographic level. In a worst-case scenario (compromised service
account, legal hold, or exit from GCP), the ability to revoke the key
and render all data unreadable is a meaningful addition to the security
posture.
**Decision:** provision a customer-managed Cloud KMS key and configure
Firestore to use it via CMEK. The Firestore service agent gets
`cloudkms.cryptoKeyEncrypterDecrypter` on that key.
**Consequence:** revoking the key makes all collections unreadable
within minutes — a nuclear option for incident response. Day-to-day
access control stays in IAM + security rules. Cost: negligible
(~€0.06/month for one active key version).
**When to revisit:** never — CMEK is strictly additive. The only
downside is a ~5 ms latency increase per operation, which is invisible
at church-scale traffic.

---

## ADR-009: No A/B testing in MVP — phased introduction

**Date:** 2025-06
**Status:** accepted
**Context:** A/B testing frameworks add routing complexity,
observability requirements, and statistical interpretation overhead.
The MVP has <5 churches and no product metrics pipeline.
**Decision:** defer A/B testing entirely until Phase 3. See
[`docs/15-ab-testing-strategy.md`](15-ab-testing-strategy.md) for the
phased introduction plan and the criteria that trigger it.
**Consequence:** simpler deploy, simpler routing, simpler debugging.
Downside: we can't measure the impact of feature changes on user
behavior until the pipeline is in place.
**When to revisit:** see the trigger criteria in `15-ab-testing-strategy.md`.

---

## ADR-010: Merge activity-service into reporting-service

**Date:** 2025-06
**Status:** accepted
**Supersedes:** the implicit 5-service split in the original prompt (B)

**Context:** after building all six services with production adapters,
CI/CD, and operational docs (33 commits of empirical data), we
measured the actual overhead and security properties of each service
boundary. Data showed:

- `activity-service` had 30% infrastructure overhead (243 lines of
  boilerplate out of 798 total) — the highest ratio of any service.
- `propelauth_auth.py` was copy-pasted identically across 5 services
  (261 lines of pure duplication).
- `activity-service` and `reporting-service` are both YELLOW-zone,
  both `--no-allow-unauthenticated`, both PropelAuth-protected, and
  share domain concepts (`activity_type`, `age_band_counts`,
  `participants_total`). Reporting's `GenerateReportInput` takes
  `activities: list[dict]` — it already knows what an activity is.
- The only IAM difference was BigQuery access (reporting had
  `bigquery.dataEditor`, activity did not). This prevented a
  theoretical activity→BigQuery write — but that threat requires a
  code change which would be caught by code review + CI.

We evaluated against the Israeli defense-in-depth principle:
"multiple independent barriers, each sufficient alone." The SA
isolation between two YELLOW services was a barrier that protected
the same asset (aggregate data) against the same threats at the same
trust level. Removing it leaves five independent layers intact. See
[`docs/16-defense-in-depth.md`](16-defense-in-depth.md) for the full
analysis.

**Decision:** merge `activity-service` into `reporting-service`.
The combined service handles activity tracking (create, get, export)
AND report generation (monthly, quarterly, board export). It runs
under one Cloud Run service, one SA, one Dockerfile.

**Consequence:**
- ~350 lines of infrastructure code removed
- 1 fewer deploy job, SA, IAM binding, healthz target
- HTTP hop in admin-web KPI dashboard eliminated (export_period is
  now an internal function call)
- Duplicated PropelAuth + FakeAuth adapters eliminated
- 3 of 8 defense layers changed; 5 of 5 independent layers preserved
- Combined SA has `datastore.user` + `bigquery.dataEditor`
- Activity endpoints still cannot reach BigQuery — no code path
  exists; adding one requires review + CI

**What we kept:**
- Firestore collections remain separate (`activities` vs `reports`)
- `pii_guard` runs on every reporting ingest path
- Activity endpoints validate age-band sums via Pydantic
- PropelAuth RBAC on every endpoint

**When to revisit:** if a future requirement places activity data in
a different zone (e.g., participant-level tracking that becomes RED),
split them back. The port pattern makes this a one-day operation.

---

## ADR-011: Defense-in-depth policy as a permanent document

**Date:** 2025-06
**Status:** accepted
**Context:** the activity+reporting merge decision required a
structured evaluation of which service boundaries earn their keep.
That evaluation should be repeatable for any future merge or split.
**Decision:** create [`docs/16-defense-in-depth.md`](16-defense-in-depth.md)
as the permanent reference for how kyrk-projekt applies defense-in-
depth. It defines the decision matrix (5 yes/no questions), the
non-negotiable RED-zone boundaries, and the evaluation process for
future changes.
**Consequence:** any future service merge or split must reference this
document and answer the five evaluation questions in writing (PR
description or new ADR). No merge across zone boundaries without a
full security review + DPIA update.
**When to revisit:** when new zones or trust levels are introduced
(e.g., a BLUE zone for financial transactions).

---

## ADR-012: Cloudflare Pages + proxy for public-facing sites

**Date:** 2025-06
**Status:** accepted
**Context:** the platform has two static sites (member-portal,
wifi-intake-portal) and four dynamic services. Hosting static sites
on GCS requires 5 GCP resources (bucket + IAM + Cloud CDN + SSL cert
+ load balancer) per site. Each resource needs Terraform, costs money,
and adds an ops surface. Meanwhile, the public intake endpoint needs
DDoS protection, which Cloud Armor charges $5/policy/month for.
**Decision:** host static sites on Cloudflare Pages (free tier, global
edge, auto-SSL, auto-CDN, free DDoS). Route dynamic traffic through
Cloudflare proxy to Cloud Run (free WAF, bot detection, DDoS). All
data stays in GCP (Firestore, KMS, BigQuery in EU regions).
**Consequence:**
- Static deploys: one command (`wrangler pages deploy`) instead of 5
  GCP resources. No Terraform needed for Pages.
- DDoS + WAF: free, automatic, no Cloud Armor cost.
- Resilience: static sites survive a GCP outage (edge-served).
- Ops: one more vendor (Cloudflare) but fewer things to configure.
- Sovereignty: Cloudflare edge caches are EU-restricted on free plan
  for .se domains. All persistent data (Firestore, KMS) stays in GCP
  `europe-north1`. Cloudflare sees only the HTTP request/response, not
  the database contents.
- New failure mode: if Cloudflare goes down, flip DNS to direct Cloud
  Run URLs (5 min manual rollback). Documented in
  [`architecture/cloudflare-edge.md`](architecture/cloudflare-edge.md).
**What we do NOT move to Cloudflare:**
- Backend services (need Python + Firestore + KMS — Cloudflare Workers
  can't run our stack)
- Secrets (stay in GCP Secret Manager with per-secret IAM)
- Encryption keys (stay in GCP KMS with CMEK)
- Database (stays in GCP Firestore with EU multi-region)
**When to revisit:** if Cloudflare changes their free-tier terms, or if
we need to serve dynamic content from edge (evaluate Cloudflare Workers
at that point, but it would require a JS rewrite).
