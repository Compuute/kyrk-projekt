# 16 — Defense-in-Depth Policy

This document defines how kyrk-projekt applies defense-in-depth,
why certain services are kept separate, and how to evaluate future
merge or split decisions. It is the reference document for any
architecture review that touches service boundaries or IAM.

## The principle

> Multiple independent barriers, each sufficient alone, so that
> breaching one does not compromise the asset.

"Independent" is the key word. Two instances of the same PropelAuth
middleware are not independent — they fail from the same cause (a
PropelAuth bug). A PropelAuth check + a Cloud Run
`--no-allow-unauthenticated` gate ARE independent — they use
different code, different infrastructure, different credentials.

## How we classify assets

| Zone | Asset | Sensitivity | Example |
|---|---|---|---|
| **RED** | Identity data (names, personnummer, phone, email), certificates, membership status | **Critical** — GDPR personal data, affects individuals directly | `members` collection, `certificates` collection |
| **YELLOW** | Aggregate counts, KPI/ROI metrics, age-band breakdowns, finance buckets | **Internal** — commercially sensitive but not personal | `activities` collection, `reports` collection, BigQuery dataset |
| **GREEN** | Public content, AI prompt templates, wifi portal copy | **Public** — designed to be visible | `content.json`, OpenClaw outputs after human review |

## How we evaluate service boundaries

A service boundary earns its keep **only** if it creates an
**independent security barrier** that protects a **different asset**
or protects the **same asset against a different threat class**.

### Decision matrix

| Question | If YES → keep separate | If NO → merge is safe |
|---|---|---|
| Do the two services handle data in **different zones** (RED vs YELLOW)? | **YES** — zone boundary = security boundary | |
| Does one service have a **public attack surface** and the other doesn't? | **YES** — separation isolates the blast radius of a public RCE | |
| Does one service hold **cryptographic credentials** (KMS) the other doesn't? | **YES** — separation prevents credential exposure from a lower-trust surface | |
| Are the two services in the **same zone** with the **same trust level**? | | **Safe to merge** — separation is overhead without security benefit |
| Does the separation prevent a threat that **requires a code change** to exploit? | | **Safe to merge** — code review + CI catch code changes; IAM separation is redundant |

### Applied to current architecture

| Service pair | Same zone? | Same trust? | Public surface? | KMS? | Decision |
|---|---|---|---|---|---|
| `membership-intake` + `membership-service` | Both RED | **No** — intake is public, membership is authenticated | intake = `--allow-unauthenticated` | membership has KMS | **KEEP SEPARATE** — public surface must not access KMS |
| `activity-service` + `reporting-service` | Both YELLOW | **Yes** — both authenticated, both aggregate | neither public | neither has KMS | **MERGED** — separation was overhead without security benefit |
| `certificate-service` vs merged `reporting-service` | RED vs YELLOW | **No** — different zones | neither public | neither has KMS (cert uses Firestore only) | **KEEP SEPARATE** — zone boundary |
| `admin-web` vs everything | UI only | N/A — admin-web holds zero state | admin-web is public | no | **KEEP SEPARATE** — it's a different kind of thing (UI vs API) |

## The five remaining independent layers (post-merge)

After merging activity + reporting into one YELLOW service, every
data access still passes through at least **five independent barriers**:

```
Layer 1: Cloud Run --no-allow-unauthenticated        [NETWORK]
  ↓ only authenticated requests reach the container
Layer 2: PropelAuth RBAC middleware                    [APPLICATION]
  ↓ only users with the right role proceed
Layer 3: Pydantic input validation                     [APPLICATION]
  ↓ only well-formed payloads are accepted
Layer 4: pii_guard recursive field check               [DATA]
  ↓ any forbidden field name → 422 reject
Layer 5: Firestore collection + doc-id scoping         [DATA]
  ↓ activities and reports are separate collections;
    doc-ids are {church_id}__{id} preventing cross-church reads
```

Each layer uses a different mechanism and fails independently.
Removing any one does NOT expose the asset to the remaining threats.

## RED-zone boundaries — non-negotiable

The following separations must **never** be merged without a full
security review + DPIA update:

### 1. membership-intake ↔ membership-service

**Why:** intake's public POST endpoint (`--allow-unauthenticated`) is
the platform's most exposed surface. If it shares a process with
membership-service, an RCE in the public endpoint gives the attacker:

- `cloudkms.cryptoKeyEncrypterDecrypter` on the `member-pn` key
  → can decrypt every member's personnummer
- `datastore.user` on the `members` collection
  → can read/write all member records

With separation:
- Intake's SA has `datastore.user` on `intake_submissions` only
- Intake's SA has NO KMS access
- An RCE in intake gives: pending submission data (which is redacted
  after approval anyway) but NOT the decryption key

This is the most important security boundary in the platform.

### 2. certificate-service ↔ reporting-service

**Why:** certificates contain member_id references and live in RED.
Reports contain only aggregates and live in YELLOW. Merging them
would put RED-zone data access and YELLOW-zone data access behind
the same SA, the same process, and the same error-handling code path.

### 3. admin-web ↔ any backend

**Why:** admin-web is a UI layer. It holds zero domain state. Every
action is a forwarded HTTP call with the user's own bearer token.
Merging it into a backend would give the backend session-cookie-
handling responsibilities and HTML-rendering code paths that increase
the attack surface without adding security.

## YELLOW-zone merges — evaluated and safe

### activity + reporting → reporting-service (DONE)

**Date:** 2025-06
**Evaluation:**

The two services handled data in the same zone (YELLOW), at the same
trust level (both authenticated, both aggregate), with the same Cloud
Run config (`--no-allow-unauthenticated`), the same auth middleware
(PropelAuth), and the same Pydantic validation pattern.

The only IAM difference was that reporting had `bigquery.dataEditor`
and activity did not. This prevented a theoretical attack path:
"activity endpoint accidentally writes to BigQuery." But that path
required a code change (importing BigQueryExportPort in activity code),
which would be caught by code review (2 reviewers for IAM-adjacent
changes per CONTRIBUTING.md) and CI (tests would fail on unexpected
imports).

**Risk assessment:**
- Threat: activity endpoint → BigQuery write
- Probability: requires code change + review bypass = **extremely low**
- Impact: YELLOW data in BigQuery = **low** (aggregates, not PII)
- Risk: extremely low × low = **negligible**

**Cost of separation:**
- 350+ lines of infrastructure boilerplate
- 1 extra deploy job, SA, IAM binding, healthz monitor
- HTTP hop in admin-web's KPI dashboard
- Duplicated PropelAuth + FakeAuth adapters
- 30% infra-overhead ratio in the smallest service

**Decision:** merge. The five remaining independent layers provide
sufficient defense-in-depth for YELLOW-zone aggregates.

## How to evaluate future merges

Before merging any two services, answer these questions in writing
(in a PR description or an ADR):

1. **Are they in the same zone?** If no → stop. Do not merge across
   zone boundaries.
2. **Does either have a public attack surface?** If one is
   `--allow-unauthenticated` and the other is not → stop.
3. **Does either hold cryptographic credentials** (KMS, signing keys)
   that the other doesn't? If yes → stop.
4. **What independent layer does the separation provide** that no
   other layer provides? If the answer is "SA isolation between two
   services with the same trust level" → that's a candidate for merge.
5. **What is the threat that the separation prevents?** If it requires
   a code change to exploit → merge is safe (code review catches it).
6. **What is the impact if the threat materializes?** If the impact is
   YELLOW-level (aggregate leak, no PII) → merge is safe.
7. **What is the cost of keeping them separate?** Count the infra
   files, deployment jobs, duplicated code, and operational overhead.

Document the answers. Put them in
[`docs/14-architecture-decisions.md`](14-architecture-decisions.md)
as a new ADR. Get 2 reviewers to sign off.

## How to evaluate future splits

Before splitting a service into two, answer:

1. **Does the new boundary create an independent security layer?**
   If no → don't split. You're adding operational overhead for no
   security benefit.
2. **Does the split separate a public surface from a privileged one?**
   If yes → split is justified.
3. **Does the split isolate cryptographic credentials?**
   If yes → split is justified.
4. **Is the service handling two different zones?**
   If yes → split is mandatory.

## What to read next

- [`14-architecture-decisions.md`](14-architecture-decisions.md) — ADR
  for every major choice including the activity+reporting merge
- [`05-security-principles.md`](05-security-principles.md) — concrete
  security rules for code changes
- [`governance/security-review-template.md`](governance/security-review-template.md)
  — the PR checklist for security-sensitive changes
- [`13-runbook.md`](13-runbook.md) — incident response when a
  barrier is breached
