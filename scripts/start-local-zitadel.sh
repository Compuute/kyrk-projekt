#!/usr/bin/env bash
#
# start-local-zitadel.sh — Runs local kyrk-projekt services with Zitadel Cloud authentication.
#
# This runs the downstream backend services in memory mode (no GCP keys/Firestore needed)
# but configures their fake auth adapters to accept real Zitadel tokens.
# It runs `admin-web` in production mode to authenticate via Zitadel OIDC.

set -euo pipefail

# Zitadel Settings
ZITADEL_ISSUER_URL="https://kyrk-auth-oqvxjf.us1.zitadel.cloud"
ZITADEL_CLIENT_ID="376717918169271350"
ZITADEL_REDIRECT_URI="http://localhost:8080/login/callback"

# Retrieve client secret
if [ -z "${ZITADEL_CLIENT_SECRET:-}" ]; then
    echo "======================================================================"
    echo "Zitadel Client Secret is required to exchange authentication codes."
    echo "Please retrieve the Client Secret from the Zitadel Cloud Console under"
    echo "the 'admin-web' application configurations."
    echo "======================================================================"
    read -r -s -p "Enter Zitadel Client Secret: " ZITADEL_CLIENT_SECRET
    echo ""
fi

if [ -z "$ZITADEL_CLIENT_SECRET" ]; then
    echo "Error: Zitadel Client Secret cannot be empty." >&2
    exit 1
fi

# Activate virtualenv if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# Downstream services config
export INTAKE_BASE_URL="http://localhost:8001"
export CERTIFICATE_BASE_URL="http://localhost:8002"
export MEMBERSHIP_BASE_URL="http://localhost:8003"
export REPORTING_BASE_URL="http://localhost:8004"

# Zitadel environment variables
export ZITADEL_ISSUER_URL
export ZITADEL_CLIENT_ID
export ZITADEL_CLIENT_SECRET
export ZITADEL_REDIRECT_URI

# Storage to clean up background pids
PIDS=()

cleanup() {
    echo -e "\nStopping all services..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
        fi
    done
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "Starting downstream services (ADAPTER_MODE=memory)..."

# 1. membership-intake on port 8001
ADAPTER_MODE=memory uvicorn app.main:app --app-dir "$PROJECT_DIR/services/membership-intake" --port 8001 > /dev/null 2>&1 &
PIDS+=($!)
echo "✓ membership-intake running on $INTAKE_BASE_URL"

# 2. certificate-service on port 8002
ADAPTER_MODE=memory uvicorn app.main:app --app-dir "$PROJECT_DIR/services/certificate-service" --port 8002 > /dev/null 2>&1 &
PIDS+=($!)
echo "✓ certificate-service running on $CERTIFICATE_BASE_URL"

# 3. membership-service on port 8003
ADAPTER_MODE=memory uvicorn app.main:app --app-dir "$PROJECT_DIR/services/membership-service" --port 8003 > /dev/null 2>&1 &
PIDS+=($!)
echo "✓ membership-service running on $MEMBERSHIP_BASE_URL"

# 4. reporting-service on port 8004
ADAPTER_MODE=memory uvicorn app.main:app --app-dir "$PROJECT_DIR/services/reporting-service" --port 8004 > /dev/null 2>&1 &
PIDS+=($!)
echo "✓ reporting-service running on $REPORTING_BASE_URL"

echo "Starting admin-web (ADAPTER_MODE=production)..."

# 5. admin-web on port 8080 (running in production/Zitadel mode)
# Let's run this in the foreground so you can see logs and press Ctrl+C to exit.
ADAPTER_MODE=production uvicorn app.main:app --app-dir "$PROJECT_DIR/services/admin-web" --port 8080
