resource "google_storage_bucket" "bucket" {
  name                        = var.name
  project                     = var.project_id
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = var.public_read ? "inherited" : "enforced"

  versioning {
    enabled = true
  }

  dynamic "lifecycle_rule" {
    for_each = var.retention_days == null ? [] : [var.retention_days]
    content {
      condition {
        age = lifecycle_rule.value
      }
      action {
        type = "Delete"
      }
    }
  }
}

# Public-read access is only granted to the wifi-portal-content bucket.
# Everything else is private by default.
resource "google_storage_bucket_iam_member" "public_read" {
  count  = var.public_read ? 1 : 0
  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
