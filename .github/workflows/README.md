# GitHub Actions workflows

Two workflows live here:

| File | Trigger | What it does |
|---|---|---|
| `ci.yml` | push to `main`, PRs to `main`, manual | Runs tests + lint + terraform validate |
| `deploy.yml` | manual (`workflow_dispatch`) | Builds container images and deploys them to Cloud Run |

## ci.yml

Runs on every push and PR. Four jobs:

1. **`pytest`** — matrix over the six Python services. Each runs
   `pytest -q` against its own `requirements.txt`. Uses pip caching.
2. **`wifi-portal-tests`** — Node-based test for the static portal's
   content decision logic.
3. **`syntax-check`** — `python -m compileall` over all service code.
   Catches obvious breakage without forcing a linter style on the team.
4. **`terraform-validate`** — `terraform init -backend=false`,
   `validate`, and `fmt -check`.

No secrets required. Pure CI; no GCP access.

## deploy.yml

Manual-only by default — change the `on:` block when you're ready to
auto-deploy on push to `main`.

The deploy workflow uses **Workload Identity Federation** so no
long-lived service account keys are stored in GitHub. The setup is a
one-time GCP-side action; instructions below.

### Required GitHub repository secrets

Set these under *Settings → Secrets and variables → Actions*:

| Secret | Example | Notes |
|---|---|---|
| `GCP_PROJECT_ID` | `kyrk-projekt-dev` | The target GCP project. |
| `GCP_REGION` | `europe-north1` | Must be EU. |
| `GCP_WIF_PROVIDER` | `projects/123/locations/global/workloadIdentityPools/github/providers/github` | Full provider resource name. |
| `GCP_DEPLOYER_SA` | `sa-deployer@<project>.iam.gserviceaccount.com` | The deploy SA WIF impersonates. |
| `PROPELAUTH_URL` | `https://auth.<tenant>.propelauthtest.com` | Tenant URL — not the API key. |
| `ADMIN_NOTIFY_WEBHOOK` | `https://n8n.example/webhook/...` | n8n webhook for new pending intake. |

The PropelAuth API key, KMS key, and BigQuery dataset are **not**
GitHub secrets — they're created in GCP and referenced by name in the
workflow. The deploy SA needs `secretmanager.secretAccessor` on each
secret name listed below.

### Required GCP secrets (Secret Manager)

| Secret name | Used by | Stored value |
|---|---|---|
| `propelauth-api-key` | all 5 RED/YELLOW services | PropelAuth API key |

`gcloud secrets create propelauth-api-key --replication-policy=user-managed --locations=europe-north1,europe-west1`
then `printf 'KEY' \| gcloud secrets versions add propelauth-api-key --data-file=-`.

### One-time GCP setup

1. **Enable APIs** (in the target project):
   ```bash
   gcloud services enable \
     artifactregistry.googleapis.com \
     run.googleapis.com \
     iam.googleapis.com \
     iamcredentials.googleapis.com \
     sts.googleapis.com \
     secretmanager.googleapis.com \
     firestore.googleapis.com \
     cloudkms.googleapis.com \
     bigquery.googleapis.com
   ```

2. **Create Artifact Registry**:
   ```bash
   gcloud artifacts repositories create kyrk \
     --repository-format=docker \
     --location=europe-north1
   ```

3. **Create Workload Identity Pool + provider**:
   ```bash
   gcloud iam workload-identity-pools create github \
     --location=global \
     --display-name="GitHub Actions"

   gcloud iam workload-identity-pools providers create-oidc github \
     --location=global \
     --workload-identity-pool=github \
     --display-name="GitHub" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
     --issuer-uri="https://token.actions.githubusercontent.com"
   ```

4. **Create the deploy service account**:
   ```bash
   gcloud iam service-accounts create sa-deployer --display-name="GitHub Actions deployer"
   ```

5. **Grant the deployer the minimum roles** — least privilege only:
   ```bash
   PROJECT=<your-project-id>
   for role in \
     roles/run.admin \
     roles/artifactregistry.writer \
     roles/iam.serviceAccountUser \
     roles/secretmanager.secretAccessor; do
     gcloud projects add-iam-policy-binding $PROJECT \
       --member="serviceAccount:sa-deployer@$PROJECT.iam.gserviceaccount.com" \
       --role="$role"
   done
   ```
   Note: `iam.serviceAccountUser` is required so the deployer can
   *impersonate* (not be) the per-service runtime SAs that Terraform
   already created. The deployer never has the runtime SAs' permissions.

6. **Bind the GitHub repo to the deployer SA via WIF**:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     sa-deployer@$PROJECT.iam.gserviceaccount.com \
     --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUM>/locations/global/workloadIdentityPools/github/attribute.repository/Compuute/.github"
   ```

7. **Create the runtime service accounts** (Terraform already does this
   if you've applied the baseline). Each Cloud Run service runs as its
   own SA with only the permissions it needs:

   | Runtime SA | Roles needed |
   |---|---|
   | `sa-membership-service` | `datastore.user`, `cloudkms.cryptoKeyEncrypterDecrypter` (specific key), `secretmanager.secretAccessor` (specific secret) |
   | `sa-membership-intake` | `datastore.user`, `secretmanager.secretAccessor` (specific secret) |
   | `sa-certificate-service` | `datastore.user`, `secretmanager.secretAccessor` (specific secret) |
   | `sa-activity-service` | `datastore.user`, `secretmanager.secretAccessor` (specific secret) |
   | `sa-reporting-service` | `datastore.user`, `bigquery.dataEditor` (specific dataset), `secretmanager.secretAccessor` (specific secret) |
   | `sa-admin-web` | (no GCP roles — only forwards user tokens to Cloud Run services it invokes) |

   `sa-admin-web` additionally needs `roles/run.invoker` on each
   downstream service it calls — set those bindings explicitly.

### Running a deploy

Manually from the Actions tab → *deploy* → *Run workflow* → pick `dev`
or `prod`. The workflow:

1. Builds all six images in parallel and pushes them to Artifact Registry.
2. Deploys the four leaf services first (membership-service,
   certificate-service, activity-service, reporting-service).
3. Reads `membership-service`'s URL and deploys `membership-intake`.
4. Reads `membership-intake` and `certificate-service` URLs and deploys
   `admin-web`.
5. Prints a summary table of all deployed URLs in the run summary.

### Rollback

```bash
gcloud run services update-traffic <service> \
  --region=europe-north1 \
  --to-revisions=<previous-revision>=100
```

Cloud Run keeps revisions, so rollback is a one-line traffic shift —
no rebuild needed.

### Smoke-testing a freshly deployed service

Each service exposes `/healthz`. After the workflow completes, the
summary lists URLs; curl `<URL>/healthz` to confirm.

For admin-web, open `<URL>/login` in a browser. The MVP login flow
accepts any `user:church:role` token; production swaps in real
PropelAuth login.
