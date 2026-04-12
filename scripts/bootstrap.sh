#!/usr/bin/env bash
#
# bootstrap.sh — one-command GCP + GitHub setup for kyrk-projekt.
#
# Usage:
#   ./scripts/bootstrap.sh <environment>
#
# Example:
#   ./scripts/bootstrap.sh dev
#
# Runs (in order):
#   1. Prereq check (terraform, gcloud, gh, git)
#   2. terraform init + apply in infra/terraform/
#   3. Prompts for secret values and runs `gcloud secrets versions add`
#   4. Reads `terraform output` and sets the matching GitHub repo secrets
#      via `gh secret set`
#   5. Prints a summary with the next-step command
#
# The script is idempotent: re-running it after a partial failure picks
# up where it stopped. It never touches terraform.tfstate by itself —
# that lives in the same place terraform puts it (local by default).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_DIR/infra/terraform"

ENVIRONMENT="${1:-}"
if [ -z "$ENVIRONMENT" ]; then
  echo "usage: $0 <environment>  (e.g. dev or prod)" >&2
  exit 2
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
RESET='\033[0m'

step() { printf "\n${BOLD}==>${RESET} %s\n" "$*"; }
ok()   { printf "${GREEN}✓${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}!${RESET} %s\n" "$*"; }
die()  { printf "${RED}✗${RESET} %s\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------- prereq check
step "Checking prerequisites"
for tool in terraform gcloud git; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    die "missing required tool: $tool"
  fi
  ok "$tool found"
done
if command -v gh >/dev/null 2>&1; then
  ok "gh found (will set GitHub secrets automatically)"
  HAVE_GH=1
else
  warn "gh not found — you'll need to set GitHub secrets manually at the end"
  HAVE_GH=0
fi

# --------------------------------------------------------- terraform workspace
step "Running terraform apply in $TERRAFORM_DIR"
cd "$TERRAFORM_DIR"

if [ ! -f terraform.tfvars ]; then
  if [ -f terraform.tfvars.example ]; then
    warn "terraform.tfvars missing. Copying from example — you MUST edit it next."
    cp terraform.tfvars.example terraform.tfvars
    warn "Edit terraform.tfvars with your project_id and re-run this script."
    exit 1
  fi
  die "terraform.tfvars not found and no example to copy"
fi

terraform init -input=false
terraform apply -auto-approve

ok "terraform apply complete"

# ----------------------------------------------------- capture terraform output
step "Reading terraform outputs"
PROJECT_ID=$(terraform output -raw -state-out=/dev/null 2>/dev/null || true)
# Terraform does not expose project_id as an output because the user
# supplies it. Read it from terraform.tfvars directly.
PROJECT_ID=$(grep -E '^\s*project_id' terraform.tfvars | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
REGION=$(grep -E '^\s*region' terraform.tfvars | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
REGION=${REGION:-europe-north1}

DEPLOYER_SA=$(terraform output -raw deployer_service_account)
WIF_PROVIDER=$(terraform output -raw wif_provider)
KMS_KEY=$(terraform output -raw kms_member_pn_key_id)
AR_REPO=$(terraform output -raw artifact_registry_repo)

ok "project_id:   $PROJECT_ID"
ok "region:       $REGION"
ok "deployer SA:  $DEPLOYER_SA"
ok "WIF provider: $WIF_PROVIDER"
ok "KMS key:      $KMS_KEY"
ok "AR repo:      $AR_REPO"

# --------------------------------------------------------------- fill secrets
step "Populating Secret Manager secret versions"
prompt_and_add_secret() {
  local name="$1"
  local label="$2"
  # Check if a version already exists — idempotency.
  if gcloud secrets versions list "$name" --project="$PROJECT_ID" --limit=1 \
      --format='value(name)' 2>/dev/null | grep -q .; then
    ok "$name already has a version — skipping"
    return 0
  fi
  read -r -s -p "$label: " VAL
  echo
  if [ -z "$VAL" ]; then
    warn "$name left empty — skipping (you'll need to add it manually later)"
    return 0
  fi
  printf '%s' "$VAL" | gcloud secrets versions add "$name" \
    --project="$PROJECT_ID" \
    --data-file=- >/dev/null
  ok "$name set"
}

prompt_and_add_secret "propelauth-api-key"       "PropelAuth API key"
prompt_and_add_secret "anthropic-api-key"        "Anthropic API key"
prompt_and_add_secret "fortnox-client-id"        "Fortnox client id"
prompt_and_add_secret "fortnox-client-secret"    "Fortnox client secret"
prompt_and_add_secret "admin-notify-webhook"     "Admin notify webhook URL"
prompt_and_add_secret "reporting-service-token"  "Reporting service n8n token (optional)"

# ----------------------------------------------------- GitHub repo secrets
step "Setting GitHub repo secrets"
if [ "$HAVE_GH" = "1" ]; then
  read -r -p "PropelAuth tenant URL (for GitHub secret PROPELAUTH_URL): " PROPELAUTH_URL
  read -r -p "Admin notify webhook URL (for GitHub secret ADMIN_NOTIFY_WEBHOOK): " WEBHOOK

  gh secret set GCP_PROJECT_ID       --body "$PROJECT_ID"       --env "$ENVIRONMENT"
  gh secret set GCP_REGION           --body "$REGION"           --env "$ENVIRONMENT"
  gh secret set GCP_WIF_PROVIDER     --body "$WIF_PROVIDER"     --env "$ENVIRONMENT"
  gh secret set GCP_DEPLOYER_SA      --body "$DEPLOYER_SA"      --env "$ENVIRONMENT"
  gh secret set PROPELAUTH_URL       --body "$PROPELAUTH_URL"   --env "$ENVIRONMENT"
  gh secret set ADMIN_NOTIFY_WEBHOOK --body "$WEBHOOK"          --env "$ENVIRONMENT"
  ok "GitHub environment secrets set for $ENVIRONMENT"
else
  cat <<EOF

Set these six secrets manually under Settings → Environments → $ENVIRONMENT:

  GCP_PROJECT_ID       = $PROJECT_ID
  GCP_REGION           = $REGION
  GCP_WIF_PROVIDER     = $WIF_PROVIDER
  GCP_DEPLOYER_SA      = $DEPLOYER_SA
  PROPELAUTH_URL       = <your PropelAuth tenant URL>
  ADMIN_NOTIFY_WEBHOOK = <your n8n webhook URL>
EOF
fi

# ---------------------------------------------------------------- summary
step "Bootstrap complete"
cat <<EOF

${GREEN}kyrk-projekt is ready to deploy to $ENVIRONMENT.${RESET}

Next step:

  gh workflow run deploy.yml -f environment=$ENVIRONMENT
  gh run watch

Or from the browser: Actions → deploy → Run workflow → $ENVIRONMENT.

After the deploy finishes:

  gh workflow run e2e.yml -f environment=$ENVIRONMENT

For manual smoke test:

  for svc in membership-service membership-intake certificate-service \\
             activity-service reporting-service admin-web; do
    URL=\$(gcloud run services describe \$svc \\
      --region=$REGION --project=$PROJECT_ID \\
      --format='value(status.url)')
    printf "%-22s " "\$svc"
    curl -s -o /dev/null -w "%{http_code}\\n" "\$URL/healthz"
  done
EOF
