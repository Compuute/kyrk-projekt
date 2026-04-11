# Declare secret resources only. Actual secret values are populated manually
# via `gcloud secrets versions add` or a privileged CI job. Terraform must
# never hold production secret material in state.
resource "google_secret_manager_secret" "secret" {
  for_each  = toset(var.names)
  project   = var.project_id
  secret_id = each.value

  replication {
    user_managed {
      replicas {
        location = "europe-north1"
      }
      replicas {
        location = "europe-west1"
      }
    }
  }
}
