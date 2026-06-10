# Backup infrastructure — GCS bucket for Firestore exports.
# Follows: well-architected-guidelines.md § 8. Disaster Recovery.
#
# The nightly.yml workflow exports Firestore to this bucket daily.
# 90-day lifecycle rule ensures old backups are auto-deleted.

resource "google_storage_bucket" "firestore_backups" {
  name     = "${var.project_id}-firestore-backups"
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true

  # Auto-delete backups older than 90 days (GDPR + cost optimization)
  lifecycle_rule {
    condition {
      age = var.retention_days
    }
    action {
      type = "Delete"
    }
  }

  # Prevent accidental deletion of the bucket itself
  force_destroy = false
}

# The deployer SA needs permission to export Firestore into this bucket.
# This is the minimal IAM needed for the nightly backup job.
resource "google_project_iam_member" "deployer_firestore_export" {
  project = var.project_id
  role    = "roles/datastore.importExportAdmin"
  member  = "serviceAccount:${var.deployer_sa_email}"
}

# The deployer SA also needs write access to the backup bucket.
resource "google_storage_bucket_iam_member" "deployer_backup_write" {
  bucket = google_storage_bucket.firestore_backups.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${var.deployer_sa_email}"
}
