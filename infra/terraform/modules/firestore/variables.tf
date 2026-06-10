variable "project_id" { type = string }
variable "region" { type = string }

variable "project_number" {
  description = "The project number (numeric). Required for the Firestore service agent IAM binding when CMEK is enabled."
  type        = string
  default     = ""
}

variable "cmek_key_id" {
  description = "Full resource name of the KMS key for CMEK encryption. Leave empty to use Google-managed encryption."
  type        = string
  default     = ""
}

variable "location_id" {
  description = "Firestore database location (e.g. eur3, europe-north1)"
  type        = string
  default     = "eur3"
}

