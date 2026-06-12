# Agent Operating Model (AOM)

How **agentic AI groups** develop and operate kyrk-projekt safely. This is the
umbrella that ties the existing pieces together — [CLAUDE.md](../../CLAUDE.md)
(rules), [ops-contract.yaml](../../ops/ops-contract.yaml) (ops domain),
[agent-access-policy.md](agent-access-policy.md) (KYA access), the feature-flag
governance ([docs/27](../27-feature-flag-workflow.md)), and the CI gates — into
one model. Aligned with Anthropic's guidance for building effective, safe
agents. Decision record: [ADR-021](../14-architecture-decisions.md).

## 1. Premise

The team is AI agent groups (Claude Code and peers) plus human owners. Agents do
most of the **building and diagnosis**; humans own the **irreversible decisions**
and remain accountable. The model assumes agents are fast and capable but can be
**confidently wrong** — so safety comes from *deterministic guardrails and clear
human gates*, not from trusting agent judgment. (This repo's CLAUDE.md was itself
written after confident-but-unverified claims wasted cycles — the AOM encodes the
fix.)

## 2. Principles (Anthropic-aligned)

1. **Deterministic guardrails over judgment.** An agent cannot talk past a red CI
   check. Enforcement lives in code (gates), not in prompts.
2. **Humans own the irreversible; agents own the reversible-and-verified.**
3. **Least privilege per role** — an agent gets the minimum access for its job,
   added in layers (KYA), never blanket.
4. **Verify against the target** — no confident-unverified claims (CLAUDE.md
   RULE 1). Diagnosis is separated from fix; pushback with data is the job,
   sycophancy is a bug.
5. **Observable & attributable** — every agent action is visible and traceable to
   a role, without putting AI names in commits (RULE 4).
6. **Start simple, grow in layers.** Capability is earned, not granted up front.

## 3. Agent roles & envelopes

A Claude Code session may wear several hats in one turn; the *envelope* is the
union of these constraints, enforced by the gates in §4–6.

| Role | May touch | Privilege | May NOT |
|---|---|---|---|
| **Builder** | code on a branch, tests, docs | write to branch; open PR | merge, deploy, touch RED-zone PII, change released tags |
| **Reviewer** | the diff, CI output | read + comment | push, merge, approve its own work |
| **Ops / SRE** | logs, status, deploy-state (read-only) via [`ops-cli.py`](../../ops/ops-cli.py) | read-only diagnosis (KYA Layer 1) | any `ops-contract` forbidden op; anything in `approval_required` without a human |
| **Research / Diagnose** | repo, docs, read-only MCP | read-only | any write |

No role merges its own PR, deploys to prod, or acts on a §5 gate alone.

## 4. The guardrail stack (deterministic räcken)

Green CI is a **precondition for human review** — an agent's PR is not "done"
until the räcken are green. Each gate stops a specific agent failure mode:

| Gate (CI) | Enforces | Stops |
|---|---|---|
| **commit hygiene (no AI committers)** | RULE 4 — committer is the human owner | AI names leaking into history |
| **repo guard** (architecture / security / coverage / docs-freshness / TLS) | hexagonal boundaries, no PII in webhooks, ≥60% cov, no `CERT_NONE`, docs match code | confident-but-wrong structural/security changes |
| **flag hygiene** | every flag has owner+type+expiry; expired flags fail | flag debt accumulating |
| **flag advisor** | risk signal on high-blast-radius diffs | shipping risky changes unflagged |
| **ci / pytest, frontend-e2e / playwright** | behaviour | functional regressions |
| **terraform-plan (PR)** / **terraform-apply (approval)** | infra changes reviewed before applied | unreviewed infra mutation |

## 5. Human-approval gates — agent MUST escalate, never act alone

Generalises [`ops-contract.yaml` → `approval_required`](../../ops/ops-contract.yaml)
to the whole team:

- **Merge to main / promote to production** (deploy is a human "promote", not an
  auto-ship — see the release-safety layer, [docs/15](../15-ab-testing-strategy.md)).
- **Prod deploy, rollback, secret rotation, terraform apply, Firestore restore**
  (ops-contract).
- **Data-model / schema changes** (migration risk).
- **Money / financial assumptions** — e.g. the year-3 funeral projections; an
  agent flags the gap, a human supplies the numbers.
- **Sovereignty / data-residency decisions** — e.g. the EU-region move
  ([ADR-017](../14-architecture-decisions.md)).
- **Changing a released semver tag** — forbidden; corrections ship as the next
  version (global RULE 3 — immutable evidence chain).
- **Anything touching RED-zone PII.**

## 6. Never autonomous (forbidden, any role)

Per [`ops-contract.yaml` → `forbidden_operations`](../../ops/ops-contract.yaml):
delete Firestore data, modify IAM / billing / DNS, disable security (auth, KMS,
WAF), read/export RED-zone PII, `git push --force` to main. Plus global RULE 3
(released tags immutable) and RULE 4 (no AI committers). Off-limits regardless of
role or approval.

## 7. Attribution & audit (Know Your Agent)

- **Committer = the human owner** (RULE 4) → accountability is unambiguous and the
  evidence chain stays clean for security/audit buyers.
- **Per-agent trail lives outside the git author field.** Auditing *which agent
  did what* uses: (a) an `Agents:` section in the PR description (role + what it
  did), and (b) the session transcripts as the full record. So agent work is
  fully traceable without AI names in commits.
- **Access** (which MCP server / token / scope an agent has) is registered in
  [agent-access-policy.md](agent-access-policy.md), mirroring the GDPR
  sub-processor register.

## 8. Verification contract

Every agent change is **verified against the concrete target** (RULE 1) and the
räcken are green **before** a human reviews. A claim that "X works" is not
accepted until it is run against X. Being wrong after verification is fine; being
right without verification does not count.

## 9. Access & least privilege

The tooling/permission layer is [agent-access-policy.md](agent-access-policy.md):
read-first, layered (diagnose → bindings → write), scoped tokens, and
write/deploy kept in the controlled pipeline (`deploy.yml` + `ops-cli`), never on
an always-on agent MCP.

## 10. Observability & escalation

Agents and humans watch the same read-only signals (KYA Layer 1: Pages Functions
logs, build/deploy status). Automated escalation thresholds are in
[`ops-contract.yaml` → `escalation`](../../ops/ops-contract.yaml) (e.g. 5xx > 5%
for 5 min → notify + consider rollback in dev only).

## 11. How it all connects

```
                    Agent Operating Model  (this doc — the umbrella)
                               │
   ┌───────────┬──────────────┼───────────────┬─────────────────┐
 CLAUDE.md   ops-contract   agent-access     flag governance   CI gates
 (rules)     (ops domain)   (KYA access)     (release safety)  (enforcement)
 RULE 1-4    approval/       MCP register     docs/27 +         commit-hygiene,
             forbidden/      + layers         flags hygiene/    repo-guard,
             escalation                       advisor           e2e, terraform
```

The AOM is the policy; the CI gates are the mechanism; the humans are the
accountable owners. New capabilities (a new MCP server, a new agent role, a write
permission) are added by amending this model and its referenced docs — in a PR,
reviewed by a human — never ad hoc.
