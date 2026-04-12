# 12 — Operations

How to deploy, roll back, monitor, and respond to incidents.

## TL;DR

```bash
# First time: bootstrap GCP + GitHub secrets
./scripts/bootstrap.sh dev

# Every deploy: trigger the workflow
gh workflow run deploy.yml -f environment=dev
gh run watch

# Rollback a bad service
gcloud run services update-traffic <service> \
  --region=europe-north1 \
  --to-revisions=<previous-revision>=100
```

## First-time setup

The bootstrap script at `scripts/bootstrap.sh` does everything in order:

```bash
cd kyrk-projekt
./scripts/bootstrap.sh dev
```

It will:

1. **Check prerequisites.** `terraform`, `gcloud`, `gh`, `git`. Fails
   fast if anything is missing.
2. **Run `terraform init && terraform apply`** in `infra/terraform/`.
   This creates:
   - Artifact Registry repo `kyrk`
   - Cloud KMS keyring `kyrk` + key `member-pn` (annual rotation)
   - Workload Identity Pool `github` + provider (restricted to one repo)
   - Deployer service account `sa-deployer` with 4 minimum roles
   - All 6 runtime service accounts with per-service IAM bindings
   - Firestore database (EU multi-region)
   - BigQuery dataset `kyrk_analytics`
   - All GCS buckets
   - Secret Manager secret resources (empty — no values yet)
3. **Prompt you for secret values** and populate them:
   - `propelauth-api-key`
   - `anthropic-api-key`
   - `fortnox-client-id`, `fortnox-client-secret`
   - `admin-notify-webhook`
4. **Set GitHub repo secrets** via `gh secret set` using the Terraform
   outputs for `GCP_DEPLOYER_SA`, `GCP_WIF_PROVIDER`, etc.
5. **Print a summary** with next-step commands.

The script is idempotent — re-running it after a partial failure picks
up from where it stopped.

## Running a deploy

Manual from the command line (if `gh` is installed):

```bash
gh workflow run deploy.yml -f environment=dev
gh run watch
```

Or from the browser: *Actions → deploy → Run workflow → dev*.

Either way, the workflow:

1. Builds all six container images in parallel and pushes them to
   Artifact Registry with the git SHA as the tag.
2. Deploys the four leaf services in parallel: `membership-service`,
   `certificate-service`, `activity-service`, `reporting-service`.
3. Reads `membership-service`'s URL and deploys `membership-intake`.
4. Reads `membership-intake` + `certificate-service` URLs and deploys
   `admin-web`.
5. Prints a summary table of all deployed URLs.

`prod` deploys pause at the first job for required-reviewer approval
(if you've configured the environment protection rule — see
[`.github/workflows/README.md`](../../.github/workflows/README.md)).

After the deploy finishes, `e2e.yml` runs automatically and curls
`/healthz` on every service. If anything comes back non-200, the e2e
workflow fails and the run summary highlights which service is unhealthy.

## Rollback

Cloud Run keeps the last 100 revisions per service. Rolling back is a
single traffic shift — no rebuild, no downtime:

```bash
# List revisions
gcloud run revisions list \
  --service=membership-service \
  --region=europe-north1

# Find the one you want to go back to (typically the previous healthy one)
gcloud run services update-traffic membership-service \
  --region=europe-north1 \
  --to-revisions=membership-service-00042-xyz=100
```

For a full platform rollback:

```bash
for svc in membership-service membership-intake certificate-service \
           activity-service reporting-service admin-web; do
  PREV=$(gcloud run revisions list --service=$svc --region=europe-north1 \
    --format='value(metadata.name)' --limit=2 | tail -1)
  gcloud run services update-traffic $svc --region=europe-north1 \
    --to-revisions=$PREV=100
done
```

## Monitoring

### Health checks

Every service exposes `GET /healthz` returning `{"status": "ok"}`. Cloud
Run uses this as a liveness probe. You can also curl it manually:

```bash
for svc in membership-service membership-intake certificate-service \
           activity-service reporting-service admin-web; do
  URL=$(gcloud run services describe $svc --region=europe-north1 --format='value(status.url)')
  printf "%-22s " "$svc"
  curl -s -o /dev/null -w "%{http_code}\n" "$URL/healthz"
done
```

### Logs

Cloud Run streams stdout/stderr into Cloud Logging automatically:

```bash
# Recent logs for one service
gcloud run services logs read membership-service --region=europe-north1 --limit=50

# Tail logs for one service
gcloud run services logs tail membership-service --region=europe-north1

# Search for errors in the last hour across all services
gcloud logging read \
  'resource.type="cloud_run_revision" AND severity>=ERROR AND timestamp>="'$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)'"' \
  --limit=50
```

### Audit events

Every RED-zone write emits an audit event. Query them from Firestore:

```bash
gcloud firestore query \
  --collection-group=audit_events \
  --filter='church_id==stjohannes'
```

Or from the Firestore console → `audit_events` collection. They contain
`{actor_user_id, church_id, action, target_id, at}` — nothing else.

### Sanitizer alarms

If the n8n sanitizer rejects a payload before it reaches Anthropic, the
workflow posts to `ADMIN_NOTIFY_WEBHOOK` with the run ID and a hash of
the offending payload (not the payload itself). Set up a Slack or email
bridge on that webhook.

## Common incidents

### A service is returning 500s

1. `gcloud run services logs tail <service> --region=europe-north1` →
   look for the exception.
2. If it's a config error (missing env var), check the deploy workflow
   ran with the right environment secrets.
3. If it's a downstream error (Firestore / KMS / PropelAuth), check
   each of those consoles for quota, outage, or permission issues.
4. If it's not obvious in 5 minutes: **roll back** to the previous
   revision (see above) and investigate on a branch.

### A deploy failed mid-flight

The deploy workflow uses parallel jobs for independent services and
sequential jobs for dependent ones. If `membership-service` deploy
fails, `membership-intake` deploy is skipped automatically (it's in
`needs:`). The earlier services may have already deployed — that's
fine, they're independently rollback-able.

To recover: fix the problem, re-run the workflow. The deploy workflow
is idempotent per service — Cloud Run creates a new revision each time.

### Someone pushed a bad commit to main

You don't need to revert immediately. Roll back Cloud Run to the
previous revision (see above), then open a PR that reverts the bad
commit. CI + code review stays in the loop — no manual `git push
--force`, ever.

### Suspected PII leaked to Anthropic

Treat as a security incident. Follow
[`04-ai-boundaries.md#incident-response`](04-ai-boundaries.md):

1. Stop the n8n workflow immediately (`n8n` UI → deactivate).
2. Capture the `run_id` of the offending call.
3. Request data deletion from Anthropic per your contract. Zero-retention
   is configured for the kyrk tenant by default, but confirm it was
   active for that call.
4. File a DPIA update and notify affected individuals if the risk
   assessment requires it.
5. Root-cause: how did the field get past `reporting-service.pii_guard`?
   That's the failure that matters.
6. Fix, add a regression test, do a post-mortem.

### Suspected unauthorized RED access

1. Query `audit_events` for the suspicious user / time window.
2. Revoke the user in PropelAuth immediately.
3. Rotate the PropelAuth API key (generate new + `gcloud secrets
   versions add`).
4. Follow up with a forced role-review across all churches.
5. Post-mortem.

## Scaling knobs

| Setting | Default | Where |
|---|---|---|
| Max instances (public services) | 5 | `deploy.yml` flags |
| Max instances (RED services) | 3 | `deploy.yml` flags |
| Memory per service | 512Mi | `deploy.yml` flags |
| Min instances (n8n) | 1 | `infra/terraform/main.tf` |
| Rate limit (intake) | 5 / 60s / key | service constructor |

Bump these in small, reversible increments — don't 10x everything at
once, and watch the cost dashboard.

## Cost watch

Roughly for a single small church in dev:

| Resource | Est. monthly |
|---|---|
| Cloud Run (scale-to-zero for 5/6 services) | ~€1-3 |
| Firestore (free tier covers MVP) | €0 |
| Cloud KMS (one key, low traffic) | <€0.10 |
| Cloud Storage (4 buckets) | <€0.50 |
| Secret Manager (6 secrets) | <€0.10 |
| BigQuery (empty) | €0 |
| n8n Cloud Run (min 1 instance) | ~€5-10 |
| Anthropic API (quarterly calls, JSON only) | ~€1-2 per run |
| **Total** | **~€10-20/month** |

Production with 5 churches and real traffic: budget ~€40-80/month.

## What to read next

- [`10-getting-started.md`](10-getting-started.md) — local dev setup
- [`11-development-guide.md`](11-development-guide.md) — how to add
  features safely
- [`governance/policies.md`](governance/policies.md) — retention,
  deletion, access review cadence
- [`governance/security-review-template.md`](governance/security-review-template.md)
  — the checklist for RED-zone PRs
- [`.github/workflows/README.md`](../../.github/workflows/README.md) —
  full deploy workflow reference
