# Reserved dataset for future analytics. Empty in MVP — no tables, no views.
resource "google_bigquery_dataset" "dataset" {
  dataset_id  = var.dataset_id
  project     = var.project_id
  location    = "EU"
  description = "kyrk-projekt analytics. YELLOW only. No identity fields permitted."

  # Table expiration default is 90 days for anything created in dev.
  default_table_expiration_ms = 90 * 24 * 60 * 60 * 1000
}
