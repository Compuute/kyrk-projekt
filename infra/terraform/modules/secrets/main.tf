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

# Per-secret accessor bindings. Each entry in `var.accessors` is
# `{secret = "<name>", member = "serviceAccount:..."}`. We bind ONE
# accessor at a time so revoking access for a single SA is a one-line
# Terraform diff and never affects the others.
resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = {
    for binding in var.accessors :
    "${binding.secret}::${binding.member}" => binding
  }

  project   = var.project_id
  secret_id = google_secret_manager_secret.secret[each.value.secret].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = each.value.member
}
