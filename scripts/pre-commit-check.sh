#!/usr/bin/env bash
# Pre-commit guard — run before every commit.
# Catches vendor lock-in and PII leaks before they reach CI.
#
# Install: cp scripts/pre-commit-check.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# Or: make install-hooks

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
FAIL=0

echo "Running pre-commit checks..."

# 1. Vendor lock-in: no vendor imports in routes or ports
echo -n "  Vendor lock-in check... "
VENDOR_IN_ROUTES=$(grep -rn "^import httpx\|^import anthropic\|^import google\|^from google\|^import firebase\|^import requests\|^import boto3" \
  services/*/app/api/*.py services/*/app/ports/*.py 2>/dev/null || true)
if [ -n "$VENDOR_IN_ROUTES" ]; then
  echo -e "${RED}FAIL${NC}"
  echo "  Vendor imports in routes/ports (must be in adapters/):"
  echo "  $VENDOR_IN_ROUTES"
  FAIL=1
else
  echo -e "${GREEN}OK${NC}"
fi

# 2. PII in webhooks/notifications: check for contact_phone, personal_number in outgoing payloads
echo -n "  PII leak check... "
PII_IN_PAYLOADS=$(grep -rn "contact_phone\|personal_number\|contact_email" \
  services/*/app/adapters/webhook_*.py services/*/app/adapters/*notification*.py 2>/dev/null \
  | grep -v "blocked\|BLOCKED\|filter\|FILTER\|#" || true)
if [ -n "$PII_IN_PAYLOADS" ]; then
  echo -e "${RED}FAIL${NC}"
  echo "  Potential PII in outgoing adapters:"
  echo "  $PII_IN_PAYLOADS"
  FAIL=1
else
  echo -e "${GREEN}OK${NC}"
fi

# 3. Auth check: every POST route must have _require_session
echo -n "  Auth on POST routes... "
UNAUTHED=$(grep -n "@router.post" services/*/app/api/routes.py 2>/dev/null | while read line; do
  FILE=$(echo "$line" | cut -d: -f1)
  LINENO=$(echo "$line" | cut -d: -f2)
  NEXT_20=$(sed -n "$((LINENO+1)),$((LINENO+20))p" "$FILE")
  if ! echo "$NEXT_20" | grep -q "_require_session\|healthz\|api_token\|X-API-Token"; then
    echo "  $line"
  fi
done)
if [ -n "$UNAUTHED" ]; then
  echo -e "${RED}FAIL${NC}"
  echo "  POST routes without auth:"
  echo "  $UNAUTHED"
  FAIL=1
else
  echo -e "${GREEN}OK${NC}"
fi

# 4. Secrets check: no hardcoded tokens/keys
echo -n "  Secrets check... "
SECRETS=$(git diff --cached --diff-filter=ACMR -U0 | grep -iE "api_key\s*=\s*[\"'][a-z0-9]|token\s*=\s*[\"'][a-z0-9]|password\s*=\s*[\"'][a-z0-9]" | grep -v "test\|fake\|mock\|example\|placeholder" || true)
if [ -n "$SECRETS" ]; then
  echo -e "${RED}FAIL${NC}"
  echo "  Possible hardcoded secrets:"
  echo "  $SECRETS"
  FAIL=1
else
  echo -e "${GREEN}OK${NC}"
fi

if [ $FAIL -ne 0 ]; then
  echo ""
  echo -e "${RED}Pre-commit checks FAILED. Fix issues above before committing.${NC}"
  exit 1
fi

echo -e "${GREEN}All pre-commit checks passed.${NC}"
