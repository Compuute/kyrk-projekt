# Firestore in native mode. One database per project. EU region only.
resource "google_firestore_database" "default" {
  project                     = var.project_id
  name                        = "(default)"
  location_id                 = "eur3" # EU multi-region (Belgium + Netherlands)
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"

  # Deletion protection is enabled by default in production. For dev you may
  # want to flip this — leave TODO here intentionally.
  # deletion_policy = "DELETE"
}
