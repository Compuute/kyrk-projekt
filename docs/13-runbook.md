# 13 — Incident runbook

Concrete, copy-paste playbooks for the five most likely incidents.
Each section follows the same shape:

1. **Symptoms** — how you know this is happening.
2. **Severity** — page now, office hours, or just-log-it.
3. **Immediate action** — first 5 minutes.
4. **Diagnosis** — how to find root cause.
5. **Remediation** — fix or mitigate.
6. **Post-mortem prompts** — what to write up afterwards.

If none of these fit, fall back to the more general
[`12-operations.md`](12-operations.md) and escalate.

## Prerequisites for the commands

Every command block assumes:

```bash
export PROJECT=kyrk-projekt-dev
export REGION=europe-north1
```

If you deployed to another project / region, swap those values.

---

## 1. Service is returning 5xx

### Symptoms

- `/healthz` returns 500, or the e2e workflow is red.
- A user reports "the admin UI is broken" or "intake form doesn't
  submit".
- Cloud Run error rate spikes in the console.

### Severity

- **Production** → page immediately.
- **Dev** → fix during office hours unless it blocks a demo.

### Immediate action (5 min)

```bash
# 1. Confirm which services are unhealthy
for svc in membership-service membership-intake certificate-service \
           activity-service reporting-service admin-web; do
  URL=$(gcloud run services describe $svc --region=$REGION --project=$PROJECT --format='value(status.url)')
  printf "%-22s " "$svc"
  curl -s -o /dev/null -w "%{http_code}\n" "$URL/healthz"
done

# 2. If one service is down, roll it back immediately:
gcloud run revisions list --service=<service> --region=$REGION --project=$PROJECT --limit=5
gcloud run services update-traffic <service> --region=$REGION --project=$PROJECT \
  --to-revisions=<previous-healthy-revision>=100
```

Rollback is safe: Cloud Run keeps old revisions, and the application
is stateless — rollback affects only the binary in front of Firestore.

### Diagnosis

```bash
# Recent errors for the affected service
gcloud run services logs read <service> --region=$REGION --project=$PROJECT --limit=100 \
  --format='value(textPayload)' | grep -iE 'error|exception|traceback'

# Startup failures (most common cause after a deploy): check the env vars
gcloud run services describe <service> --region=$REGION --project=$PROJECT \
  --format='yaml(spec.template.spec.containers[0].env)'
```

Common root causes, in order of frequency:

1. **Missing env var after deploy** (e.g. forgot to set `KMS_KEY_NAME`
   on membership-service → factory raises `RuntimeError` at startup).
   Fix: redeploy with the right env block.
2. **Downstream unreachable** — Firestore, KMS, or PropelAuth is
   throttling, down, or permission-denied.
   Fix: check the linked console, check IAM bindings.
3. **Bad commit merged to main** — a logic bug surfaces once real
   traffic hits it.
   Fix: roll back (above), then revert the commit in a PR.

### Post-mortem prompts

- Why didn't the ci.yml / e2e.yml catch this before prod?
- Is there a test we can add?
- Does `docs/12-operations.md` need updating?

---

## 2. Deploy workflow failed mid-flight

### Symptoms

- `deploy.yml` shows a red X on one job.
- Some services were deployed but not all (the later tiers are
  skipped automatically via `needs:`).

### Severity

- **Prod**: treat as incident until verified rollback is in place.
- **Dev**: no urgency.

### Immediate action

```bash
# Check what's currently running in each service
for svc in membership-service membership-intake certificate-service \
           activity-service reporting-service admin-web; do
  REV=$(gcloud run services describe $svc --region=$REGION --project=$PROJECT \
    --format='value(status.latestReadyRevisionName)')
  TRAFFIC=$(gcloud run services describe $svc --region=$REGION --project=$PROJECT \
    --format='value(status.traffic[0].revisionName)')
  printf "%-22s traffic=%s latest=%s\n" "$svc" "$TRAFFIC" "$REV"
done
```

If the traffic revision and latest ready revision differ, a deploy
started but never shifted traffic. Either:

- **The new revision is broken** → do nothing. Traffic is already on
  the old revision. Fix the problem and re-run the workflow.
- **The new revision is good but shift failed** → shift traffic
  manually:
  ```bash
  gcloud run services update-traffic <service> --region=$REGION \
    --project=$PROJECT --to-latest
  ```

### Diagnosis

Open the failed Actions run in the browser. Three common failure
modes:

1. **Docker build failed** — usually a bad Dockerfile change. Look at
   the `build-and-push` job logs. Fix locally with `docker build`
   then push.
2. **Cloud Run deploy failed** — usually IAM or image not found. Look
   at the specific `deploy-<service>` job. Check that the runtime SA
   exists and that the image tag is correct.
3. **WIF auth failed** — the deployer SA lost `iam.workloadIdentityUser`
   or the GitHub repo binding is wrong. Check
   `terraform state show google_service_account_iam_member.deployer_wif_user`.

### Remediation

- Fix the root cause in a PR (even for dev).
- Re-run the failed workflow: *Actions → deploy → Re-run failed jobs*.
  The workflow is idempotent per service — Cloud Run just creates a
  new revision.

### Post-mortem prompts

- Did CI catch this? If not, what check would?
- Should we add the check to `ci.yml` or `local-ci.sh`?

---

## 3. Bad commit pushed to main

### Symptoms

- Someone force-merged a PR that shouldn't have shipped.
- Prod is degraded or showing incorrect behavior.
- You need to get back to green fast *without* rewriting history.

### Severity

- **Prod with real users**: page immediately.
- **Dev**: urgent but not panic.

### Immediate action

Never `git push --force` to main. Roll back Cloud Run first, fix with
a revert PR second:

```bash
# Step 1: roll all affected services back
for svc in <affected-service-names>; do
  PREV=$(gcloud run revisions list --service=$svc --region=$REGION \
    --project=$PROJECT --format='value(metadata.name)' --limit=2 | tail -1)
  gcloud run services update-traffic $svc --region=$REGION --project=$PROJECT \
    --to-revisions=$PREV=100
  echo "$svc -> $PREV"
done

# Step 2: revert the commit in git
git fetch origin
git revert <bad-sha>
git push origin HEAD:refs/heads/revert-<bad-sha>
gh pr create --base main --head revert-<bad-sha> \
  --title "revert: <short description>" \
  --body "Rolls back <bad-sha> — see incident notes in docs/13-runbook.md."
```

Let CI run on the revert PR. Review it like any other PR. Merge.
Then re-run `deploy.yml` to get main back onto its own revision.

### Diagnosis

- `git log --oneline main..<bad-sha>^` — what commits are affected?
- `gh pr view <pr-num>` — who approved and when?

### Post-mortem prompts

- Did required reviewers approve this? If yes, what did they miss?
- Was the `governance/security-review-template.md` checklist filled in?
- Should this class of change require an e2e test before merge?

---

## 4. Suspected PII leaked to Anthropic

### Symptoms

- `n8n` logs show a workflow succeeded but the payload sent to
  Anthropic included a blocked field.
- A user or auditor reports seeing identity data in an OpenClaw
  output stored in `gs://<project>-openclaw-pending/`.
- The sanitizer did NOT abort — which is the failure mode that
  matters.

### Severity

**Always page immediately, any environment, any scale.** This is a
GDPR incident.

### Immediate action (first 10 minutes)

```bash
# 1. Stop all n8n workflows that call Anthropic
#    Open n8n UI → Workflows → deactivate:
#    - quarterly_openclaw_analysis
#    - any other workflow with sanitizerProfile=yellow-only
#
# 2. Capture the run ID and the offending payload hash
#    (n8n records the run_id in the execution log; do NOT download
#    the raw payload — it is PII)

# 3. Tell the admin team — use the secure channel, not email
#    Template: "Potential PII leak to Anthropic, run_id=<id>,
#    workflow=<name>. Workflows deactivated. Standing by for DPIA."
```

### Diagnosis

1. **Confirm the leak happened.** Pull the run metadata from n8n
   (not the payload). Look at the workflow's `sanitizerProfile`.
2. **Reproduce without sending.** Write a regression test in
   `reporting-service/tests/test_pii_guard.py` that uses the same
   shape of payload. Confirm the test fails with current code.
3. **Identify how the field slipped.**
   - Was it a new field added upstream that isn't in the profile
     whitelist?
   - Was the sanitizer step missing from the workflow?
   - Did the profile list change and accidentally allow a bad field?

### Remediation

1. **Fix the sanitizer profile or pii_guard first.** Write the
   regression test. Make it pass.
2. **Redeploy reporting-service with the fix** before reactivating
   any Anthropic-calling workflow.
3. **Request data deletion from Anthropic** per your DPA. Zero-retention
   is configured for the kyrk tenant by default, but confirm it was
   active for the affected call.
4. **Update the incident log.** DPIA review is mandatory before
   reactivating n8n workflows.
5. **Notify affected individuals** only if the risk assessment
   requires it — consult the DPO, not your gut.

### Post-mortem prompts

- Why didn't `pii_guard` catch this? (It should have — that's the
  whole point of defense in depth.)
- Is there a new field name we need to add to `FORBIDDEN_FIELDS`?
- Should we add an automated daily test that pushes known-bad
  payloads through the sanitizer to verify it rejects them?
- Who reviewed the workflow JSON that allowed this? Is there a
  review gap?

---

## 5. Suspected unauthorized RED access

### Symptoms

- Audit events show `member.read` or `member.update` from an actor
  who should not have been in that church.
- An admin reports seeing data they don't recognize.
- A PropelAuth log shows a token minted at an unusual time or
  location.

### Severity

**Page immediately.** Unauthorized access to identity data is the
worst-case scenario this platform is designed to prevent.

### Immediate action

```bash
# 1. Revoke the suspicious user in PropelAuth immediately
#    (PropelAuth UI → Users → Block user)
#
# 2. Rotate the PropelAuth API key
gcloud secrets versions add propelauth-api-key \
  --project=$PROJECT --data-file=<(printf 'NEW-KEY-FROM-PROPELAUTH')

#    Then force all services to reload:
for svc in membership-service membership-intake certificate-service \
           activity-service reporting-service; do
  gcloud run services update $svc --region=$REGION --project=$PROJECT \
    --update-env-vars=PROPELAUTH_KEY_ROTATED_AT=$(date +%s)
done

# 3. Capture the audit events for the suspect time window
gcloud firestore query --collection-group=audit_events \
  --filter='actor_user_id==<suspect-id>' \
  --project=$PROJECT
```

### Diagnosis

1. **Correlate audit events with PropelAuth access logs.** Does the
   actor's session make sense (time, IP, device)?
2. **Check for privilege escalation.** Did a `secretary` suddenly
   perform `member.deactivate`? Check the role enforcement in
   `membership_service.py`.
3. **Check cross-church access.** Did any read return a member from
   a different church_id than the caller's? If yes, that's an
   existence-disclosure bug that violates the 404 rule.

### Remediation

1. **Revoke the user**, rotate PropelAuth key (already done above).
2. **Export the suspect audit events to a secured incident folder**
   outside the production project.
3. **Force a role review** across every church — every admin must
   re-confirm their user list.
4. **File a DPIA update** within 72 hours if personal data was
   confirmed accessed.
5. **Notify affected individuals** per the risk assessment.

### Post-mortem prompts

- How did the user get into the system? Stolen credentials?
  Accidentally granted role? Session hijack?
- Does our logging capture enough to answer "who saw what"?
- Should certain audit events trigger automatic alerts?
- Is there a missing test for cross-church access on this endpoint?

---

## Escalation ladder

| Severity | Who to page | Within |
|---|---|---|
| PII leak (any scale) | Admin + DPO | 10 min |
| Unauthorized RED access | Admin + DPO | 10 min |
| Prod service down | On-call admin | 30 min |
| Dev service down | Team channel | 4 hours |
| Failed deploy | Author of last commit | Next working day |

## Incident log template

Every incident should produce a single markdown file in
`incidents/YYYY-MM-DD-short-slug.md` with:

```markdown
# <date> — <short slug>

## Summary
What happened, in one paragraph.

## Timeline
- `HH:MM` alert fired
- `HH:MM` first response
- `HH:MM` contained
- `HH:MM` resolved

## Root cause
The actual technical reason, not the first thing you noticed.

## Impact
- Users affected: ...
- Data affected: ...
- Duration: ...

## What worked
- ...

## What didn't
- ...

## Follow-ups
- [ ] <owner> — <action> — <due>
```

Keep it short and honest. The goal is that next time you read it,
you learn something.
