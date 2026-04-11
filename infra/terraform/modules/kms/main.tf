# Cloud KMS keyring + symmetric key for member personal_number encryption.
#
# Scope: ONE keyring, ONE key. Each Cloud Run service that needs to
# encrypt/decrypt is granted `cloudkms.cryptoKeyEncrypterDecrypter` on
# this specific key — never on the keyring or project.

resource "google_kms_key_ring" "kyrk" {
  name     = "kyrk"
  location = var.region
  project  = var.project_id
}

resource "google_kms_crypto_key" "member_pn" {
  name     = "member-pn"
  key_ring = google_kms_key_ring.kyrk.id
  purpose  = "ENCRYPT_DECRYPT"

  # Rotate the underlying key material annually. Old versions stay
  # available for decryption of historical ciphertexts.
  rotation_period = "31536000s" # 365 days

  # Prevent accidental destruction. To actually delete you must
  # explicitly remove this lifecycle block in a separate change.
  lifecycle {
    prevent_destroy = true
  }
}
