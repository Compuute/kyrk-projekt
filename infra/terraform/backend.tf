# Remote state backend — shared GCS bucket with object versioning and native
# locking, so multiple developers (and CI) operate on one consistent state.
# Per-environment state is isolated via terraform workspaces (dev/prod), stored
# at gs://kyrk-projekt-tfstate/terraform/<workspace>.tfstate.
#
# The state bucket is created out-of-band (gcloud), NOT managed by this config,
# to avoid a chicken-and-egg dependency on its own backend.
#
# Usage per environment:
#   terraform workspace select dev   # or: prod
#   terraform plan  -var-file=terraform.tfvars.dev
#   terraform apply -var-file=terraform.tfvars.dev
terraform {
  backend "gcs" {
    bucket = "kyrk-projekt-tfstate"
    prefix = "terraform"
  }
}
