# Workload Identity Federation — lets GitHub Actions impersonate the
# deployer SA without any long-lived service account keys.
#
# After `terraform apply` set these GitHub repo secrets:
#   GCP_WIF_PROVIDER  = google_iam_workload_identity_pool_provider.github.name
#   GCP_DEPLOYER_SA   = google_service_account.deployer.email
#
# Both values are exposed as Terraform outputs.

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "WIF pool for GitHub Actions deploys"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Restrict to ONE GitHub repository. Without this attribute_condition
  # any repo on github.com could potentially exchange a token for the
  # deployer SA — much too broad.
  attribute_condition = "attribute.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Bind the configured GitHub repo to the deployer SA.
resource "google_service_account_iam_member" "deployer_wif_user" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
}
