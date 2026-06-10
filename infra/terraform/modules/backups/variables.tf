variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for the backup bucket."
  type        = string
}

variable "deployer_sa_email" {
  description = "Email of the deployer service account that runs backup jobs."
  type        = string
}

variable "retention_days" {
  description = "Number of days to retain backups before auto-deletion."
  type        = number
  default     = 90
}
