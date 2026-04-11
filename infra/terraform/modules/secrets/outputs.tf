output "secret_ids" {
  description = "Map of secret name -> full secret resource id."
  value       = { for name, s in google_secret_manager_secret.secret : name => s.id }
}
