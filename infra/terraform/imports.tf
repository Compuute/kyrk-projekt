# One-time adoption of bootstrap-created resources into state.
# sa-terraform must exist before terraform-apply can run as it (it cannot
# create itself), so a project owner creates it by hand — see
# docs/12-operations.md. This block makes the first apply import it instead
# of failing on "already exists". Safe to delete after that apply.

import {
  to = google_service_account.terraform
  id = "projects/${var.project_id}/serviceAccounts/sa-terraform@${var.project_id}.iam.gserviceaccount.com"
}
