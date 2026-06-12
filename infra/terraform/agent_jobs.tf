# Agent-infrastruktur — Fas 1 i docs/28-agentisk-driftmodell.md.
#
# Scheduler → Pub/Sub är trigger-rörläggningen för agent-workers
# (rapportagenten först). Workers prenumererar när de landar; tills dess
# är schemat pausat (var.enable_agent_schedules) och publicerade
# meddelanden utan prenumerant släpps helt enkelt.
#
# Säkerhetsmodell (AOM §9 + agent-access-policy): agenterna får en egen
# identitet från dag ett så att varje åtgärd är attribuerbar i audit-
# loggar, men inga roller förrän den första workern landar i en granskad
# PR — least privilege, förmåga läggs till i lager.

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

resource "google_service_account" "agent_worker" {
  account_id   = "sa-agent-worker"
  display_name = "AI agent worker runtime"
  project      = var.project_id
}

resource "google_cloud_scheduler_job" "agent_report_monthly" {
  name    = "agent-report-monthly"
  project = var.project_id
  region  = var.region

  description = "Trigger för rapportagenten: månadsrapport (YELLOW-aggregat) till styrelsen."
  schedule    = "0 6 1 * *" # 06:00 den 1:a varje månad
  time_zone   = "Europe/Stockholm"
  paused      = !var.enable_agent_schedules

  pubsub_target {
    topic_name = google_pubsub_topic.agent_jobs.id
    data       = base64encode(jsonencode({ job = "monthly-report" }))
  }
}
