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

Every job in this workflow declares `environment: ${{ inputs.environment }}`.
That means GitHub looks up the environment named `dev` or `prod` (whichever
the operator picked when triggering the run) and applies its protection
rules and secrets to the job. See the **GitHub environments** section
below for the recommended setup.

The deploy workflow uses **Workload Identity Federation** so no
long-lived service account keys are stored in GitHub. Terraform creates
the WIF pool, provider, and deployer SA — see step 1 in the GCP setup
section below.

### Required GitHub repository / environment secrets

These can be set at the *repository* level (apply to all environments)
or at the *environment* level (override per env — recommended for
`prod`). Find them under *Settings → Secrets and variables → Actions*
or *Settings → Environments → <env> → Add secret*.

| Secret | Example | Scope recommendation |
|---|---|---|
| `GCP_PROJECT_ID` | `kyrk-projekt-dev` | per environment |
| `GCP_REGION` | `europe-north1` | repo |
| `GCP_WIF_PROVIDER` | `projects/123/locations/global/workloadIdentityPools/github/providers/github` | per environment |
| `GCP_DEPLOYER_SA` | `sa-deployer@<project>.iam.gserviceaccount.com` | per environment |
| `PROPELAUTH_URL` | `https://auth.<tenant>.propelauthtest.com` | per environment |
| `ADMIN_NOTIFY_WEBHOOK` | `https://n8n.example/webhook/...` | per environment |

The PropelAuth API key, KMS key, and BigQuery dataset are **not**
GitHub secrets — they live in GCP Secret Manager / Cloud KMS / BigQuery
and are referenced by name in the workflow. The deploy SA needs
`secretmanager.secretAccessor` on each secret (Terraform grants it).

## GitHub environments

Create two GitHub environments — `dev` and `prod` — under
*Settings → Environments → New environment*. The deploy workflow
references both via `environment: ${{ inputs.environment }}`.

### Recommended protection rules

| Rule | `dev` | `prod` |
|---|---|---|
| Required reviewers | none | at least 1 (a board-approved admin) |
| Wait timer | 0 | 5 minutes (gives reviewers time to react) |
| Deployment branches | `main` and feature branches | `main` only |
| Environment secrets | `GCP_PROJECT_ID=kyrk-projekt-dev` etc. | `GCP_PROJECT_ID=kyrk-projekt-prod` etc. |

### Why per-environment secrets matter

A repo-level secret leaks across `dev` and `prod` — anyone who can
trigger a `dev` deploy can read the secret. Per-environment secrets
make `prod` credentials only readable inside a job that has been
gated by the prod required-reviewer rule.

### How to configure

1. Open *Settings → Environments → New environment*. Type `dev`. Save.
2. Set environment-scoped secrets: `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`,
   `GCP_DEPLOYER_SA`, `PROPELAUTH_URL`, `ADMIN_NOTIFY_WEBHOOK`.
3. Repeat for `prod`. For prod, also enable:
   - **Required reviewers** → add the admin team / specific people.
   - **Deployment branches** → restrict to `main`.
   - **Wait timer** → 5 minutes (defense in depth — catches accidental
     prod triggers before they actually start).
4. Optionally add the same `GCP_REGION=europe-north1` at the repo
   level if both environments use the same region (likely).

### Running a deploy against an environment

From *Actions → deploy → Run workflow*, pick `dev` or `prod`. The
workflow's `environment: ${{ inputs.environment }}` blocks make GitHub:

- Look up the environment by that name
- Apply its protection rules (so a `prod` run will pause for reviewer
  approval before any job starts)
- Inject the environment-scoped secrets into every job

If you didn't create a `prod` environment but pick `prod` from the
dropdown, the workflow will fail at the secret-resolution step — that's
intentional.

## GCP setup

### Option A: Terraform (recommended)

```bash
cd kyrk-projekt/infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your project_id and github_repository
terraform init
terraform plan
terraform apply
```

This creates:

- Artifact Registry repo (`kyrk`)
- Cloud KMS keyring (`kyrk`) + symmetric key (`member-pn`)
- Workload Identity Pool (`github`) + provider (`github`) restricted
  to your `github_repository`
- Deployer SA (`sa-deployer`) with the four minimum roles
- All six runtime SAs (`sa-membership-service`, etc.) with their
  per-service IAM bindings (Firestore, KMS, BigQuery, run.invoker)
- All Secret Manager secrets with per-secret accessor bindings (only
  the services that need each secret get accessor on it)
- Firestore database (EU multi-region)
- BigQuery dataset (`kyrk_analytics`)
- All GCS buckets

After `apply`, capture the outputs:

```bash
terraform output deployer_service_account
terraform output wif_provider
terraform output kms_member_pn_key_id
terraform output artifact_registry_repo
```

Use them as the values for `GCP_DEPLOYER_SA`, `GCP_WIF_PROVIDER`,
and the `KMS_KEY_NAME` env var in `deploy.yml`.

### Option B: gcloud (manual)

If you prefer not to use Terraform, the same setup as a script:

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

3. **Create Workload Identity Pool + provider** (restrict to one repo):
   ```bash
   gcloud iam workload-identity-pools create github \
     --location=global \
     --display-name="GitHub Actions"

   gcloud iam workload-identity-pools providers create-oidc github \
     --location=global \
     --workload-identity-pool=github \
     --display-name="GitHub" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
     --attribute-condition='attribute.repository=="Compuute/.github"' \
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
   `iam.serviceAccountUser` is required so the deployer can *impersonate*
   (not be) the per-service runtime SAs. The deployer never has the
   runtime SAs' permissions.

6. **Bind the GitHub repo to the deployer SA via WIF**:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     sa-deployer@$PROJECT.iam.gserviceaccount.com \
     --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUM>/locations/global/workloadIdentityPools/github/attribute.repository/Compuute/.github"
   ```

7. **Create the runtime service accounts** with their IAM bindings.
   This is what `iam_bindings.tf` does — copy the role list below if
   you're going manual:

   | Runtime SA | Roles |
   |---|---|
   | `sa-membership-service` | `datastore.user`, `cloudkms.cryptoKeyEncrypterDecrypter` on the `member-pn` key, `secretmanager.secretAccessor` on `propelauth-api-key` |
   | `sa-membership-intake` | `datastore.user`, `secretmanager.secretAccessor` on `propelauth-api-key` and `admin-notify-webhook` |
   | `sa-certificate-service` | `datastore.user`, `secretmanager.secretAccessor` on `propelauth-api-key` |
   | `sa-activity-service` | `datastore.user`, `secretmanager.secretAccessor` on `propelauth-api-key` |
   | `sa-reporting-service` | `datastore.user`, `bigquery.dataEditor` on the `kyrk_analytics` dataset, `secretmanager.secretAccessor` on `propelauth-api-key` |
   | `sa-admin-web` | `run.invoker` on `certificate-service` (and any other private downstream services) |

### Required GCP secrets (Secret Manager)

Terraform creates the secret resources but never holds the values.
Populate them after `terraform apply`:

```bash
printf 'YOUR-KEY' | gcloud secrets versions add propelauth-api-key --data-file=-
printf 'YOUR-KEY' | gcloud secrets versions add anthropic-api-key --data-file=-
printf 'YOUR-KEY' | gcloud secrets versions add fortnox-client-id --data-file=-
printf 'YOUR-KEY' | gcloud secrets versions add fortnox-client-secret --data-file=-
printf 'YOUR-WEBHOOK' | gcloud secrets versions add admin-notify-webhook --data-file=-
```

## Running a deploy

Manually from the Actions tab → *deploy* → *Run workflow* → pick `dev`
or `prod`. The workflow:

1. Resolves the environment-scoped secrets.
2. Builds all six images in parallel and pushes them to Artifact Registry.
3. Deploys the four leaf services first (membership-service,
   certificate-service, activity-service, reporting-service).
4. Reads `membership-service`'s URL and deploys `membership-intake`.
5. Reads `membership-intake` and `certificate-service` URLs and deploys
   `admin-web`.
6. Prints a summary table of all deployed URLs in the run summary.

For `prod`, GitHub will pause at the first job and wait for a required
reviewer to approve.

## Rollback

```bash
gcloud run services update-traffic <service> \
  --region=europe-north1 \
  --to-revisions=<previous-revision>=100
```

Cloud Run keeps revisions, so rollback is a one-line traffic shift —
no rebuild needed.

## Smoke-testing a freshly deployed service

Each service exposes `/healthz`. After the workflow completes, the
summary lists URLs; curl `<URL>/healthz` to confirm.

For admin-web, open `<URL>/login` in a browser. The MVP login flow
accepts any `user:church:role` token; production swaps in real
PropelAuth login.
