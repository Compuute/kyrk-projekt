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

variable "github_repository" {
  description = "Owner/repo of the GitHub repository allowed to impersonate sa-deployer via WIF."
  type        = string
  default     = "Compuute/.github"
}
