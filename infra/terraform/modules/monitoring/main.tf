# Monitoring module — Uptime checks, alert policies, notification channels,
# and billing budget alerts.
#
# Follows the Well-Architected Guidelines:
# - Section 6: Observability & Monitoring
# - Section 7: Alerting & Uptime Checks
# - Section 2.1: Proactive Budget Alerts

# ============================================================================
# Notification Channel — email
# ============================================================================

resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "Alert email (${var.environment})"
  type         = "email"

  labels = {
    email_address = var.notification_email
  }
}

# ============================================================================
# Uptime Checks — one per public Cloud Run service
# ============================================================================

resource "google_monitoring_uptime_check_config" "service" {
  for_each = var.public_services

  project      = var.project_id
  display_name = "uptime-${each.key}-${var.environment}"
  timeout      = "10s"
  period       = var.uptime_check_period

  http_check {
    path         = each.value
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${each.key}-${data.google_project.current.number}.${var.region}.run.app"
    }
  }
}

data "google_project" "current" {
  project_id = var.project_id
}

# ============================================================================
# Alert Policy — Uptime check failures (2+ regions failing)
# ============================================================================

resource "google_monitoring_alert_policy" "uptime_failure" {
  project      = var.project_id
  display_name = "Uptime check failure (${var.environment})"
  combiner     = "OR"

  conditions {
    display_name = "Uptime check failing"
    condition_threshold {
      filter          = "resource.type = \"uptime_url\" AND metric.type = \"monitoring.googleapis.com/uptime_check/check_passed\""
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "300s"

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.host"]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.id,
  ]

  alert_strategy {
    auto_close = "1800s"
  }
}

# ============================================================================
# Alert Policy — Cloud Run 5xx error rate > 1% for 5 minutes
# ============================================================================

resource "google_monitoring_alert_policy" "error_rate" {
  project      = var.project_id
  display_name = "Cloud Run 5xx rate > 1% (${var.environment})"
  combiner     = "OR"

  conditions {
    display_name = "5xx error rate elevated"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.id,
  ]

  alert_strategy {
    auto_close = "1800s"
  }
}

# ============================================================================
# Alert Policy — Cloud Run P95 latency > 5s for 10 minutes
# ============================================================================

resource "google_monitoring_alert_policy" "high_latency" {
  project      = var.project_id
  display_name = "Cloud Run P95 latency > 5s (${var.environment})"
  combiner     = "OR"

  conditions {
    display_name = "P95 latency elevated"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
      comparison      = "COMPARISON_GT"
      threshold_value = 5000
      duration        = "600s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.id,
  ]

  alert_strategy {
    auto_close = "1800s"
  }
}

# ============================================================================
# Billing Budget Alert (optional — only created if billing_account_id is set)
# ============================================================================

resource "google_billing_budget" "project" {
  count = var.billing_account_id != "" ? 1 : 0

  billing_account = var.billing_account_id
  display_name    = "kyrk-${var.environment}-monthly-budget"

  budget_filter {
    projects               = ["projects/${data.google_project.current.number}"]
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(var.monthly_budget_eur)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }
}
