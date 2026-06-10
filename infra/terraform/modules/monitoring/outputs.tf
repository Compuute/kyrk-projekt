output "notification_channel_id" {
  description = "ID of the email notification channel for alerting."
  value       = google_monitoring_notification_channel.email.id
}

output "uptime_check_ids" {
  description = "Map of service name to uptime check ID."
  value       = { for k, v in google_monitoring_uptime_check_config.service : k => v.id }
}
