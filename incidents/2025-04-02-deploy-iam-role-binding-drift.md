# 2025-04-02 — deploy-iam-role-binding-drift

**Severity:** office hours (prod deploy failed, rollback trivial)
**Services affected:** reporting-service (deploy only, no prod traffic impact)
**Zone(s):** YELLOW, Infra
**Authors:** on-call engineer
**Incident commander:** on-call engineer

> NOTE: This is a **fictional training example** to show what
> "config drift" looks like in practice and how Terraform detects
> and fixes it. Do not use this file as a real incident log.

## Summary

The `deploy.yml` workflow failed on the `deploy-reporting-service`
job with `Permission 'bigquery.datasets.update' denied on dataset
'kyrk_analytics'`. Root cause was that someone had manually removed
the `roles/bigquery.dataEditor` binding from
`sa-reporting-service@<project>.iam.gserviceaccount.com` through
the GCP console three days earlier while "cleaning up unused
permissions". Terraform state still believed the binding existed,
so `terraform apply` had not been invoked to reconcile it.

## Timeline

- `14:08` — deploy.yml fired from a PR merge
- `14:11` — `deploy-reporting-service` job failed with the
  `Permission denied` error
- `14:12` — on-call ack'd, read the failing job logs
- `14:15` — confirmed the other five services deployed successfully
  (tier 1 parallel jobs) — only reporting-service was affected
- `14:18` — ran `terraform plan` in `infra/terraform/`:
  ```
  # google_bigquery_dataset_iam_member.reporting_service_bq will be created
    + resource "google_bigquery_dataset_iam_member" "reporting_service_bq" {
  ```
  Terraform had noticed the drift — the binding was in state but
  not in reality, so plan wanted to re-create it.
- `14:20` — ran `terraform apply`, 1 resource added in 8 seconds
- `14:22` — re-ran the failed `deploy-reporting-service` job from
  the Actions UI ("Re-run failed jobs")
- `14:24` — deploy succeeded, traffic shifted to the new revision
- `14:26` — e2e.yml ran automatically, all six healthz green
- `14:30` — incident closed
- `15:00` — follow-up postmortem call with the person who removed
  the binding (not a blame call — a "how did this happen" call)

## Root cause

**Out-of-band IAM change.** A well-meaning cleanup pass in the GCP
console removed a binding that Terraform owned. Terraform never
re-applied in the interim, so the drift was invisible until
`deploy.yml` hit the first BigQuery write.

**Second-order cause:** no `terraform plan` check in CI that would
have alerted us to the drift on every PR. The `ci.yml` runs
`terraform validate` but not `terraform plan` (which requires
real credentials).

## Impact

- **Users affected:** none — the deploy was for a new version, old
  revision was still serving all traffic
- **Data affected:** none — no writes failed, no reads failed; the
  failure was at the deploy step, before traffic shifted
- **Duration of user-visible impact:** 0
- **Financial / reputational:** the PR sat "not deployed" for 16
  minutes. A board member was waiting on the feature but was
  informed by Slack.

## What worked

- Cloud Run's "shift traffic only after the revision is healthy"
  behavior meant there was never a user-visible outage.
- Terraform detected the drift on the very next plan. It was
  impossible to miss: `plan` wanted to re-create a resource that
  was supposed to exist.
- Re-running the failed job was a single click. No manual rebuild.
- The per-tier `needs:` structure in `deploy.yml` meant only
  reporting-service's deploy was affected — the four tier-1 services
  already succeeded and did not need to re-run.

## What didn't

- CI did not detect the drift before the deploy was triggered. By
  the time we knew, we'd already wasted 10 minutes in a failed
  deploy job.
- No audit alert fired when the IAM binding was removed in the
  console. There's a Cloud Audit Log entry, but nothing was
  watching.
- The person who removed the binding did not know Terraform owned
  it. There is no marker in the GCP console that says "this is
  Terraform-managed".

## Follow-ups

- [ ] devops — add a nightly `terraform plan` job that posts the
      diff to the admin channel; any non-empty diff means drift —
      due: 2025-04-09
- [ ] devops — add a `terraform plan` step to `ci.yml` gated on
      secrets availability (skip gracefully if GCP creds not
      configured in CI) — due: 2025-04-09
- [ ] devops — add an organization-wide label convention (e.g.
      `managed_by: terraform`) to every Terraform-managed resource
      so it's obvious in the console — due: 2025-04-16
- [ ] ops — add a "pre-change checklist" one-pager for console
      changes that must include "is this Terraform-managed?" —
      due: 2025-04-16

## References

- Failed run: `Actions → deploy → run #142 → deploy-reporting-service`
- Cloud Audit Log query:
  ```
  resource.type="bigquery_dataset"
  AND protoPayload.methodName="google.iam.v1.IAMPolicy.SetIamPolicy"
  AND protoPayload.resourceName:"kyrk_analytics"
  ```
- Terraform resource: `google_bigquery_dataset_iam_member.reporting_service_bq` in `infra/terraform/iam_bindings.tf`
- Related runbook: [`docs/13-runbook.md#2-deploy-workflow-failed-mid-flight`](../docs/13-runbook.md)

---

## Lessons this example teaches

1. **Terraform state is the source of truth — but only if you run
   it.** Apply at least daily (via CI) to catch drift early.
2. **Failed deploys are not always bugs.** Sometimes they're
   signals about config drift, and that signal is valuable.
3. **Tier the deploy workflow.** Parallel tier-1 jobs meant only
   one service was affected; sequential tiers meant dependent
   services were safely skipped.
4. **Console-side edits should be rare.** Every exception should
   be logged and reviewed. A "pre-change checklist" is cheap
   insurance.
5. **Re-run failed jobs rather than redoing the whole workflow.**
   It's usually one click and preserves the green tier-1 outputs.
