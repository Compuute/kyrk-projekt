# Artifact Registry repo for the six service container images.
# The deployer SA has artifactregistry.writer at the project level
# (granted in iam_bindings.tf) so it can push to this repo.
resource "google_artifact_registry_repository" "kyrk" {
  project       = var.project_id
  location      = var.region
  repository_id = "kyrk"
  format        = "DOCKER"
  description   = "Container images for the six kyrk-projekt services"

  # Keep the last 10 versions per image to bound storage cost without
  # losing rollback targets.
  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
}
