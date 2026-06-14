# Agent-infrastruktur — Fas 1 i docs/28-agentisk-driftmodell.md.
#
# Kedjan: Cloud Scheduler → Pub/Sub-topicen agent-jobs → push-prenumeration
# med OIDC → agent-worker (Cloud Run, --no-allow-unauthenticated). Workerns
# servicekonto skapas i main.tf via local.services, som övriga tjänster;
# dess runtime-roller ligger i iam_bindings.tf.
#
# Säkerhetsmodell (AOM §9 + agent-access-policy): push-identiteten
# (sa-agent-jobs-pusher) är skild från agentens runtime-identitet
# (sa-agent-worker) — pushern får bara invoka workern, agenten får bara
# sina egna minimala runtime-roller.

resource "google_pubsub_topic" "agent_jobs" {
  name    = "agent-jobs"
  project = var.project_id

  # Drygt ett dygn: räcker för att en hängd worker ska hinna startas om
  # utan att jobb tappas, kort nog att inte ackumulera gamla triggers.
  message_retention_duration = "86600s"

  labels = {
    environment = var.environment
    purpose     = "agent-jobs"
  }
}

# Identiteten som Pub/Sub-pushen autentiserar med mot workern. Medvetet
# inte sa-agent-worker: pushern är leveransinfrastruktur, inte agenten.
resource "google_service_account" "agent_jobs_pusher" {
  account_id   = "sa-agent-jobs-pusher"
  display_name = "Pub/Sub push identity for agent-jobs"
  project      = var.project_id
}

# Pub/Sub:s service agent måste få mynta OIDC-tokens som pusher-kontot.
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.agent_jobs_pusher.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "agent_jobs_push" {
  name    = "agent-jobs-push"
  project = var.project_id
  topic   = google_pubsub_topic.agent_jobs.id

  # Workern svarar 204/500 inom sekunder; 60s täcker en kall start.
  ack_deadline_seconds = 60

  push_config {
    push_endpoint = "${module.cloud_run["agent-worker"].service_uri}/pubsub"

    oidc_token {
      service_account_email = google_service_account.agent_jobs_pusher.email
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Prenumerationen får aldrig självdö av inaktivitet — månadsjobbet är
  # glest.
  expiration_policy {
    ttl = ""
  }
}

resource "google_cloud_scheduler_job" "agent_report_monthly" {
  name    = "agent-report-monthly"
  project = var.project_id
  # Cloud Scheduler is not available in europe-north1 (var.region); use a
  # supported region. The job only publishes to the (global) Pub/Sub topic.
  region = var.scheduler_region

  description = "Trigger för rapportagenten: månadsrapport (YELLOW-aggregat) till styrelsen."
  schedule    = "0 6 1 * *" # 06:00 den 1:a varje månad
  time_zone   = "Europe/Stockholm"
  paused      = !var.enable_agent_schedules

  pubsub_target {
    topic_name = google_pubsub_topic.agent_jobs.id
    data       = base64encode(jsonencode({ job = "monthly-report" }))
  }
}
