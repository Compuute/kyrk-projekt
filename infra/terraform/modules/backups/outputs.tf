output "backup_bucket_name" {
  description = "Name of the GCS bucket used for Firestore backups."
  value       = google_storage_bucket.firestore_backups.name
}
