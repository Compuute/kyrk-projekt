resource "google_cloud_run_v2_service" "svc" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image_placeholder

      ports {
        container_port = 8080
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
  }

  # Allow invocations only from authenticated identities by default.
  # Public endpoints (e.g. membership-intake, certificate verify) are fronted
  # by a signed-request API gateway layer set up in a separate module.
}
