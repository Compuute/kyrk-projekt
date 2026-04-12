# Firestore in native mode. One database per project. EU region only.
#
# CMEK: the database is encrypted with a customer-managed Cloud KMS key
# so access can be revoked at the key level. Revoking the key makes ALL
# data in ALL collections unreadable — use only as a last-resort "nuke"
# for incident response, not as fine-grained access control. Fine-grained
# control stays in the application via IAM + security rules.

resource "google_firestore_database" "default" {
  project                     = var.project_id
  name                        = "(default)"
  location_id                 = "eur3" # EU multi-region (Belgium + Netherlands)
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"

  # CMEK — optional. Set var.cmek_key_id to the full KMS key resource name
  # to enable customer-managed encryption. Leave empty to use Google's
  # default encryption (still encrypted, just not with your own key).
  dynamic "cmek_config" {
    for_each = var.cmek_key_id != "" ? [var.cmek_key_id] : []
    content {
      kms_key_name = cmek_config.value
    }
  }

  # Deletion protection is enabled by default in production. For dev you may
  # want to flip this — leave TODO here intentionally.
  # deletion_policy = "DELETE"
}

# When CMEK is enabled, the Firestore service agent must be able to use the
# KMS key for encrypt/decrypt. This is a Google-managed service account —
# NOT one of our runtime SAs.
resource "google_kms_crypto_key_iam_member" "firestore_cmek" {
  count         = var.cmek_key_id != "" ? 1 : 0
  crypto_key_id = var.cmek_key_id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:service-${var.project_number}@gcp-sa-firestore.iam.gserviceaccount.com"
}
