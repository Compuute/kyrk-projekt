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

# Project number is needed for several IAM resources (KMS service identity,
# WIF principalSet bindings).
data "google_project" "current" {
  project_id = var.project_id
}

locals {
  # Services that deploy as Cloud Run. Each gets its own service account.
  # NOTE: activity-service was merged into reporting-service (same YELLOW
  # trust level, same asset class). The reporting-service SA now needs
  # both datastore.user and bigquery.dataEditor.
  services = [
    "membership-intake",
    "membership-service",
    "certificate-service",
    "reporting-service",
    "admin-web",
  ]

  # Buckets the platform needs. Names are project-prefixed for uniqueness.
  buckets = {
    certificates        = "certificates"        # RED — private
    wifi_portal_content = "wifi-portal-content" # GREEN — public-read
    openclaw_pending    = "openclaw-pending"    # YELLOW → GREEN (sanitized)
    reports             = "reports"             # YELLOW
  }

  # Map service name -> SA email for use in IAM bindings.
  service_account_emails = {
    for s in local.services : s => module.service_accounts[s].email
  }
}

# One service account per Cloud Run service (least privilege).
module "service_accounts" {
  for_each = toset(local.services)
  source   = "./modules/iam"

  project_id   = var.project_id
  account_id   = "sa-${each.value}"
  display_name = "${each.value} runtime"
}

# Cloud Run services. The container images come from the CI pipeline —
# the `image_placeholder` is wired in via CI, not Terraform state.
module "cloud_run" {
  for_each = toset(local.services)
  source   = "./modules/cloud-run"

  project_id        = var.project_id
  region            = var.region
  service_name      = each.value
  service_account   = module.service_accounts[each.value].email
  image_placeholder = "gcr.io/${var.project_id}/${each.value}:PLACEHOLDER"
  environment       = var.environment
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

# CI/CD deployer service account. Impersonated by GitHub Actions via WIF.
# Roles are granted in iam_bindings.tf so the locality stays in one file.
resource "google_service_account" "deployer" {
  account_id   = "sa-deployer"
  display_name = "GitHub Actions deployer"
  project      = var.project_id
}

# Cloud KMS keyring + keys. Must be created BEFORE Firestore CMEK.
module "kms" {
  source     = "./modules/kms"
  project_id = var.project_id
  region     = var.region
}

# Firestore — native mode, EU region, CMEK-encrypted.
# Revoking the KMS key makes all Firestore data unreadable — a last-resort
# incident response option. Day-to-day access control stays in IAM.
module "firestore" {
  source         = "./modules/firestore"
  project_id     = var.project_id
  region         = var.region
  project_number = data.google_project.current.number
  cmek_key_id    = module.kms.member_pn_key_id
}

# Storage buckets with lifecycle rules per purpose.
module "storage" {
  for_each = local.buckets
  source   = "./modules/storage"

  project_id     = var.project_id
  region         = var.region
  name           = "${var.project_id}-${each.value}"
  public_read    = each.key == "wifi_portal_content"
  retention_days = each.key == "openclaw_pending" ? 90 : null
}

# Secret Manager secrets + per-secret accessor bindings.
# Only the services that actually need a secret get access to it.
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

  accessors = concat(
    # PropelAuth API key — every service that authenticates users.
    [
      for s in [
        "membership-service",
        "membership-intake",
        "certificate-service",
        "reporting-service",
      ] : {
        secret = "propelauth-api-key"
        member = "serviceAccount:${local.service_account_emails[s]}"
      }
    ],
    # n8n needs Anthropic API key + Fortnox creds + admin notify webhook.
    [
      {
        secret = "anthropic-api-key"
        member = "serviceAccount:${google_service_account.n8n.email}"
      },
      {
        secret = "fortnox-client-id"
        member = "serviceAccount:${google_service_account.n8n.email}"
      },
      {
        secret = "fortnox-client-secret"
        member = "serviceAccount:${google_service_account.n8n.email}"
      },
      {
        secret = "admin-notify-webhook"
        member = "serviceAccount:${google_service_account.n8n.email}"
      },
      {
        secret = "reporting-service-token"
        member = "serviceAccount:${google_service_account.n8n.email}"
      },
    ],
    # membership-intake also needs the admin-notify-webhook for its
    # HttpNotifier when production mode is enabled.
    [
      {
        secret = "admin-notify-webhook"
        member = "serviceAccount:${local.service_account_emails["membership-intake"]}"
      },
    ],
  )
}

# BigQuery dataset — for reporting-service analytics export.
module "bigquery" {
  source     = "./modules/bigquery"
  project_id = var.project_id
  region     = var.region
  dataset_id = "kyrk_analytics"
}
