terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  # Services that deploy as Cloud Run. Each gets its own service account.
  services = [
    "membership-intake",
    "membership-service",
    "certificate-service",
    "activity-service",
    "reporting-service",
  ]

  # Buckets the platform needs. Names are project-prefixed for uniqueness.
  buckets = {
    certificates        = "certificates"         # RED — private
    wifi_portal_content = "wifi-portal-content"  # GREEN — public-read
    openclaw_pending    = "openclaw-pending"     # YELLOW → GREEN (sanitized)
    reports             = "reports"              # YELLOW
  }
}

# One service account per Cloud Run service (least privilege).
module "service_accounts" {
  for_each = toset(local.services)
  source   = "./modules/iam"

  project_id      = var.project_id
  account_id      = "sa-${each.value}"
  display_name    = "${each.value} runtime"
}

# Cloud Run services. The container images come from a future CI pipeline —
# the `image_placeholder` is wired in via CI, not Terraform state.
module "cloud_run" {
  for_each = toset(local.services)
  source   = "./modules/cloud-run"

  project_id       = var.project_id
  region           = var.region
  service_name     = each.value
  service_account  = module.service_accounts[each.value].email
  image_placeholder = "gcr.io/${var.project_id}/${each.value}:PLACEHOLDER"
  environment      = var.environment
}

# Separate Cloud Run service for n8n — minimum 1 instance for cron reliability.
module "n8n" {
  source = "./modules/cloud-run"

  project_id        = var.project_id
  region            = var.region
  service_name      = "n8n-automation"
  service_account   = google_service_account.n8n.email
  image_placeholder = "docker.n8n.io/n8nio/n8n:latest"
  environment       = var.environment
  min_instances     = 1
  max_instances     = 2
}

resource "google_service_account" "n8n" {
  account_id   = "sa-n8n-automation"
  display_name = "n8n automation runtime"
  project      = var.project_id
}

# Firestore — native mode, EU region.
module "firestore" {
  source     = "./modules/firestore"
  project_id = var.project_id
  region     = var.region
}

# Storage buckets with lifecycle rules per purpose.
module "storage" {
  for_each = local.buckets
  source   = "./modules/storage"

  project_id    = var.project_id
  region        = var.region
  name          = "${var.project_id}-${each.value}"
  public_read   = each.key == "wifi_portal_content"
  retention_days = each.key == "openclaw_pending" ? 90 : null
}

# Placeholder secrets — real values are created manually in the GCP console
# or via a separate privileged workflow. Terraform only declares the resource.
module "secrets" {
  source     = "./modules/secrets"
  project_id = var.project_id
  names = [
    "propelauth-api-key",
    "anthropic-api-key",
    "fortnox-client-id",
    "fortnox-client-secret",
    "reporting-service-token",
    "admin-notify-webhook",
  ]
}

# BigQuery dataset — reserved for future analytics. Empty in MVP.
module "bigquery" {
  source     = "./modules/bigquery"
  project_id = var.project_id
  region     = var.region
  dataset_id = "kyrk_analytics"
}
