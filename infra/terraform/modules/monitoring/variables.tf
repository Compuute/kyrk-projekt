variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region."
  type        = string
}

variable "environment" {
  description = "Environment name (dev, prod)."
  type        = string
}

variable "notification_email" {
  description = "Email address for alert notifications."
  type        = string
}

variable "public_services" {
  description = "Map of publicly-accessible Cloud Run services to their healthcheck paths."
  type        = map(string)
  default = {
    "membership-intake"   = "/healthz"
    "certificate-service" = "/healthz"
    "admin-web"           = "/healthz"
  }
}

variable "all_services" {
  description = "List of all Cloud Run service names for log-based alerting."
  type        = list(string)
  default = [
    "membership-intake",
    "membership-service",
    "certificate-service",
    "reporting-service",
    "admin-web",
  ]
}

variable "uptime_check_period" {
  description = "How often uptime checks run (in seconds). Default 300s = 5 min."
  type        = string
  default     = "300s"
}

variable "monthly_budget_eur" {
  description = "Monthly budget amount in EUR. Alerts fire at 50%, 80%, 100%."
  type        = number
  default     = 20
}

variable "billing_account_id" {
  description = "GCP billing account ID for budget alerts. Leave empty to skip budget creation."
  type        = string
  default     = ""
}
