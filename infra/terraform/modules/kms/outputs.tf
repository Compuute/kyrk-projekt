output "member_pn_key_id" {
  description = "Full resource name of the member-pn KMS key. Pass this to membership-service as KMS_KEY_NAME."
  value       = google_kms_crypto_key.member_pn.id
}

output "member_pn_key_name" {
  description = "Short name of the member-pn key (used for IAM bindings)."
  value       = google_kms_crypto_key.member_pn.name
}
