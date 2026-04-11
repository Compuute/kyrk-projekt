# Terraform baseline

GCP baseline for kyrk-projekt. Modular, minimal, and region-pinned to the EU.

## Regions

- Primary: `europe-north1` (Finland)
- Fallback: `europe-west1` (Belgium)

## Services provisioned

- Five Cloud Run services (membership-intake, membership-service,
  certificate-service, activity-service, reporting-service)
- One Cloud Run service for n8n
- Firestore (native mode, EU region)
- Cloud Storage buckets (certificates, wifi-portal-content, openclaw-pending, reports)
- Secret Manager secrets (referenced by name only — no real values in Terraform)
- One service account per Cloud Run service (least privilege)
- BigQuery dataset (future analytics — empty for MVP)

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your project_id
terraform init
terraform plan
terraform apply
```

## Cost notes

- Firestore: free tier covers MVP.
- Cloud Run: scale-to-zero for all services except n8n (min_instances = 1).
- GCS buckets: standard class, lifecycle rules for old pending reviews.
- BigQuery: provisioned but unused in MVP.

## Security

- Each Cloud Run service runs under its own service account.
- IAM bindings use specific roles (no `Editor`, no `Owner`).
- Secret Manager bindings are scoped to the single secret that service needs.
- Uniform bucket-level access is enforced on every bucket.
