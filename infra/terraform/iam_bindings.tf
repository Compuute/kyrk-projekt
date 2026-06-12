# Per-service runtime IAM bindings.
#
# This file is the canonical "what can each service do" surface. Every
# binding is the minimum required for the service to function. If a binding
# is not here, the service must not depend on the corresponding capability.
#
# All bindings use `google_*_iam_member` (not `_binding`) so removing one
# member never wipes other members on the same resource.

# ============================================================================
# membership-service — Firestore + Cloud KMS (member-pn key)
# ============================================================================

resource "google_project_iam_member" "membership_service_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${local.service_account_emails["membership-service"]}"
}

resource "google_kms_crypto_key_iam_member" "membership_service_kms" {
  crypto_key_id = module.kms.member_pn_key_id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${local.service_account_emails["membership-service"]}"
}

# ============================================================================
# membership-intake — Firestore (intake_submissions) only
# ============================================================================

resource "google_project_iam_member" "membership_intake_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${local.service_account_emails["membership-intake"]}"
}

# membership-intake forwards approvals to membership-service. The HTTP
# call carries the user's bearer token, so intake itself does not need
# run.invoker — the user's token is what proves authorization to the
# downstream service. We therefore intentionally grant nothing here for
# Cloud Run invocation.

# ============================================================================
# certificate-service — Firestore only
# ============================================================================

resource "google_project_iam_member" "certificate_service_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${local.service_account_emails["certificate-service"]}"
}

# ============================================================================
# reporting-service — Firestore + BigQuery (specific dataset)
# activity-service was merged into reporting-service. The reporting-service
# SA now covers both the `activities` and `reports` Firestore collections
# and the BigQuery analytics dataset.
# ============================================================================

resource "google_project_iam_member" "reporting_service_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${local.service_account_emails["reporting-service"]}"
}

# BigQuery is dataset-scoped via google_bigquery_dataset_iam_member, NOT
# project-level. dataEditor only on the kyrk_analytics dataset.
resource "google_bigquery_dataset_iam_member" "reporting_service_bq" {
  project    = var.project_id
  dataset_id = "kyrk_analytics"
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${local.service_account_emails["reporting-service"]}"

  depends_on = [module.bigquery]
}

# ============================================================================
# admin-web — run.invoker on private downstream services
# ============================================================================
# admin-web has no Firestore access, no KMS, no secrets. It only forwards
# user bearer tokens to other Cloud Run services. For services deployed
# with --no-allow-unauthenticated, admin-web's SA needs run.invoker so
# the request reaches the container at all (after which application-level
# auth in the downstream service decides what the request can do).

resource "google_cloud_run_v2_service_iam_member" "admin_web_invoke_certificate" {
  project  = var.project_id
  location = var.region
  name     = "certificate-service"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.service_account_emails["admin-web"]}"

  depends_on = [module.cloud_run]
}

# membership-service is --no-allow-unauthenticated (RED zone). admin-web
# reaches it for Sunday school (groups/enrollments/attendance) and
# funerals, carrying its identity in X-Serverless-Authorization (see
# admin-web app/adapters/gcp_identity.py) and the user's Zitadel bearer
# in Authorization for application-level RBAC.
resource "google_cloud_run_v2_service_iam_member" "admin_web_invoke_membership" {
  project  = var.project_id
  location = var.region
  name     = "membership-service"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.service_account_emails["admin-web"]}"

  depends_on = [module.cloud_run]
}

# reporting-service receives Sunday school attendance aggregates
# (YELLOW zone, counts only) and serves the KPI activity export.
resource "google_cloud_run_v2_service_iam_member" "admin_web_invoke_reporting" {
  project  = var.project_id
  location = var.region
  name     = "reporting-service"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.service_account_emails["admin-web"]}"

  depends_on = [module.cloud_run]
}

# membership-intake is currently --allow-unauthenticated for the public
# POST /intake endpoint. The admin endpoints under it rely on
# application-level PropelAuth checks. If you tighten intake to
# --no-allow-unauthenticated in the future, also grant admin-web here.
# resource "google_cloud_run_v2_service_iam_member" "admin_web_invoke_intake" {
#   project  = var.project_id
#   location = var.region
#   name     = "membership-intake"
#   role     = "roles/run.invoker"
#   member   = "serviceAccount:${local.service_account_emails["admin-web"]}"
#   depends_on = [module.cloud_run]
# }

# ============================================================================
# agent-worker — Firestore (audit_events) + run.invoker on reporting-service
# ============================================================================
# The report agent writes its audit trail to Firestore and calls the
# private reporting-service carrying its identity in
# X-Serverless-Authorization (same pattern as admin-web). It has no KMS,
# no secrets beyond its own env, and never touches RED collections —
# application-level RBAC in reporting-service is enforced by the agent's
# Zitadel machine-user token.

resource "google_project_iam_member" "agent_worker_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${local.service_account_emails["agent-worker"]}"
}

resource "google_cloud_run_v2_service_iam_member" "agent_worker_invoke_reporting" {
  project  = var.project_id
  location = var.region
  name     = "reporting-service"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.service_account_emails["agent-worker"]}"

  depends_on = [module.cloud_run]
}

# The Pub/Sub push identity may do exactly one thing: invoke the worker.
resource "google_cloud_run_v2_service_iam_member" "pusher_invoke_agent_worker" {
  project  = var.project_id
  location = var.region
  name     = "agent-worker"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.agent_jobs_pusher.email}"

  depends_on = [module.cloud_run]
}

# ============================================================================
# Deployer (CI/CD) — minimal roles to build, push, and deploy
# ============================================================================
# Granted ONLY what GitHub Actions needs to do its job:
# - artifactregistry.writer  : push container images
# - run.admin                : create/update Cloud Run revisions
# - iam.serviceAccountUser   : impersonate runtime SAs (NOT inherit them)
# - secretmanager.secretAccessor : read secret names referenced by deploys

resource "google_project_iam_member" "deployer_ar" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# ============================================================================
# admin-web — secret accessor for Zitadel client secret
# ============================================================================
# admin-web needs to access the Zitadel client secret at runtime to perform the OIDC
# code exchange. The secret was created manually, so we manage only the IAM binding.
resource "google_secret_manager_secret_iam_member" "admin_web_zitadel_secret" {
  project   = var.project_id
  secret_id = "zitadel-client-secret"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.service_account_emails["admin-web"]}"
}

# ============================================================================
# Terraform (IaC) — full administration of everything this module manages
# ============================================================================
# Used ONLY by terraform-apply.yml via WIF. An IaC identity must be able to
# administer what the IaC owns (IAM, KMS, secrets, WIF, buckets, monitoring),
# so least-privilege here means: a SEPARATE identity from the app deployer,
# reachable only from this repo's pipeline, with its own audit trail — not a
# short role list. sa-deployer keeps its four minimal deploy roles.

locals {
  terraform_project_roles = [
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/secretmanager.admin",
    "roles/cloudkms.admin",
    "roles/storage.admin",
  ]
}

resource "google_project_iam_member" "terraform_roles" {
  for_each = toset(local.terraform_project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.terraform.email}"
}

# Same repo-restricted WIF binding as the deployer SA.
resource "google_service_account_iam_member" "terraform_wif_user" {
  service_account_id = google_service_account.terraform.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
}
