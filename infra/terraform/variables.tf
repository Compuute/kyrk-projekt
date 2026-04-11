variable "project_id" {
  description = "GCP project id"
  type        = string
}

variable "region" {
  description = "Primary GCP region. Must be EU."
  type        = string
  default     = "europe-north1"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}
