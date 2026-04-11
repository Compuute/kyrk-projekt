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

output "deployer_service_account" {
  description = "GitHub Actions deployer SA. Bind your WIF principal to impersonate this."
  value       = google_service_account.deployer.email
}

output "kms_member_pn_key_id" {
  description = "Full resource name of the member-pn KMS key. Pass to membership-service as KMS_KEY_NAME."
  value       = module.kms.member_pn_key_id
}

output "artifact_registry_repo" {
  description = "Artifact Registry repo URL prefix used by deploy.yml."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.kyrk.repository_id}"
}

output "wif_provider" {
  description = "Full resource name of the WIF provider. Set as GitHub secret GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}
