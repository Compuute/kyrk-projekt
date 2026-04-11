output "service_account_emails" {
  description = "Per-service runtime service account emails."
  value       = { for s, m in module.service_accounts : s => m.email }
}

output "bucket_names" {
  description = "Provisioned GCS bucket names."
  value       = { for k, m in module.storage : k => m.name }
}

output "n8n_service_account" {
  description = "n8n runtime service account email."
  value       = google_service_account.n8n.email
}
