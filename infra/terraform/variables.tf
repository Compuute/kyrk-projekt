variable "project_id" {
  description = "GCP project id"
  type        = string
}

variable "region" {
  description = "Primary GCP region. Must be EU."
  type        = string
  default     = "europe-north1"
}

variable "scheduler_region" {
  description = <<-EOT
    Region for Cloud Scheduler jobs. Kept separate from var.region because
    Cloud Scheduler is not offered in every region (notably not europe-north1,
    the primary region). Scheduler only publishes to a global Pub/Sub topic,
    so this need not match where Cloud Run runs.
  EOT
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "github_repository" {
  description = "Owner/repo of the GitHub repository allowed to impersonate sa-deployer via WIF."
  type        = string
  default     = "Compuute/kyrk-projekt"
}

variable "database_location" {
  description = "Firestore database location. Default is eur3."
  type        = string
  default     = "eur3"
}

variable "notification_email" {
  description = "Email address for monitoring alert notifications."
  type        = string
  default     = "alerts@compuute.se"
}

variable "enable_agent_schedules" {
  description = "Activate the agent Cloud Scheduler jobs (agent_jobs.tf). Off by default: flip per environment once the worker that consumes agent-jobs is deployed."
  type        = bool
  default     = false
}

