#!/usr/bin/env bash
#
# local-ci.sh — run the same checks that GitHub Actions ci.yml runs,
# but on your local machine. Useful before opening a PR.
#
# Usage:
#   ./scripts/local-ci.sh            # run everything
#   ./scripts/local-ci.sh tests      # just pytest + node
#   ./scripts/local-ci.sh lint       # just compileall + terraform fmt
#   ./scripts/local-ci.sh docker     # just Dockerfile static validation
#   ./scripts/local-ci.sh terraform  # just terraform validate (requires terraform)
#
# Exit code is non-zero if any check fails.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

SERVICES=(
  membership-service
  membership-intake
  certificate-service
  activity-service
  reporting-service
  admin-web
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

# Scorecard: name => "pass" | "fail" | "skip"
declare -A SCORE

print_header() {
  printf "\n${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
  printf "${BOLD}${BLUE}  %s${RESET}\n" "$1"
  printf "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
}

mark_pass() { SCORE["$1"]="pass"; printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
mark_fail() { SCORE["$1"]="fail"; printf "  ${RED}✗${RESET} %s\n" "$1"; }
mark_skip() { SCORE["$1"]="skip"; printf "  ${YELLOW}-${RESET} %s (skipped: %s)\n" "$1" "$2"; }

# ---------------------------------------------------------------- pytest

run_pytest() {
  print_header "pytest (6 services)"
  for svc in "${SERVICES[@]}"; do
    if [ ! -d "services/$svc" ]; then
      mark_skip "$svc" "directory missing"
      continue
    fi
    # Run without -q: the summary line ("N passed in Xs") only appears
    # reliably in default output mode. With -q + warnings it's suppressed.
    OUT=$(cd "services/$svc" && python3 -m pytest --tb=short 2>&1 || true)
    SUMMARY=$(echo "$OUT" | grep -E "^=+ .*(passed|failed|error).*=+$" | tail -1 | tr -s ' ' | sed 's/^= //; s/ =$//' || true)
    if [ -z "$SUMMARY" ]; then
      SUMMARY=$(echo "$OUT" | grep -oE "[0-9]+ (passed|failed)" | tr '\n' ' ')
    fi
    if echo "$OUT" | grep -qE "failed|error" && ! echo "$OUT" | grep -qE "^=+ [0-9]+ passed"; then
      mark_fail "$svc ($SUMMARY)"
      echo "$OUT" | tail -15 | sed 's/^/    /'
    elif [ -n "$SUMMARY" ]; then
      mark_pass "$svc ($SUMMARY)"
    else
      mark_fail "$svc (no summary line — probably a crash)"
      echo "$OUT" | tail -15 | sed 's/^/    /'
    fi
  done
}

run_node_tests() {
  print_header "Node tests (wifi-intake-portal)"
  if ! command -v node >/dev/null 2>&1; then
    mark_skip "wifi-intake-portal" "node not installed"
    return
  fi
  OUT=$(cd frontend/wifi-intake-portal && node tests/test_content_decision.js 2>&1 || true)
  if echo "$OUT" | grep -q "FAIL"; then
    mark_fail "wifi-intake-portal"
    echo "$OUT" | sed 's/^/    /'
  else
    OK=$(echo "$OUT" | grep -c "ok ")
    mark_pass "wifi-intake-portal ($OK cases)"
  fi
}

# ------------------------------------------------------------------ lint

run_compileall() {
  print_header "Python syntax check (compileall)"
  if python3 -m compileall -q services automation/openclaw/import 2>/tmp/compileall.err; then
    mark_pass "compileall"
  else
    mark_fail "compileall"
    cat /tmp/compileall.err | sed 's/^/    /'
  fi
}

run_terraform_fmt() {
  print_header "Terraform fmt check"
  if ! command -v terraform >/dev/null 2>&1; then
    mark_skip "terraform fmt" "terraform not installed"
    return
  fi
  if (cd infra/terraform && terraform fmt -check -recursive) >/tmp/tf-fmt.err 2>&1; then
    mark_pass "terraform fmt"
  else
    mark_fail "terraform fmt"
    cat /tmp/tf-fmt.err | sed 's/^/    /'
  fi
}

# -------------------------------------------------------- terraform validate

run_terraform_validate() {
  print_header "Terraform validate"
  if ! command -v terraform >/dev/null 2>&1; then
    # Fall back to python-hcl2 static parse if the hcl2 module is available.
    if python3 -c "import hcl2" 2>/dev/null; then
      if python3 - <<'PY' 2>/tmp/hcl.err
import hcl2, glob, sys
ok = True
for f in sorted(glob.glob('infra/terraform/**/*.tf', recursive=True)):
    try:
        hcl2.load(open(f))
    except Exception as e:
        print(f"{f}: {e}", file=sys.stderr)
        ok = False
sys.exit(0 if ok else 1)
PY
      then
        mark_pass "terraform static parse (python-hcl2)"
      else
        mark_fail "terraform static parse (python-hcl2)"
        cat /tmp/hcl.err | sed 's/^/    /'
      fi
    else
      mark_skip "terraform validate" "terraform not installed, python-hcl2 unavailable"
    fi
    return
  fi
  if (cd infra/terraform && terraform init -backend=false -input=false && terraform validate) >/tmp/tf-val.err 2>&1; then
    mark_pass "terraform validate"
  else
    mark_fail "terraform validate"
    tail -30 /tmp/tf-val.err | sed 's/^/    /'
  fi
}

# --------------------------------------------------- Dockerfile static check

run_docker_validate() {
  print_header "Dockerfile static validation"
  python3 - <<'PY' 2>/tmp/docker.err
import re, sys
from pathlib import Path

ROOT = Path('services')
COPY_RE = re.compile(r'^\s*COPY\s+(?:--\S+\s+)*([^\s]+)\s+([^\s]+)\s*$')

services = [d.name for d in sorted(ROOT.iterdir()) if (d / 'Dockerfile').exists()]

failed = []
for svc in services:
    ctx = ROOT / svc
    df = ctx / 'Dockerfile'
    ok = True
    for ln in df.read_text().splitlines():
        m = COPY_RE.match(ln)
        if m:
            src = m.group(1)
            if not (ctx / src).exists():
                ok = False
                print(f"{svc}: COPY src '{src}' missing", file=sys.stderr)
    if not (ctx / 'app' / 'main.py').exists():
        ok = False
        print(f"{svc}: app/main.py missing", file=sys.stderr)
    if not ok:
        failed.append(svc)
    else:
        print(f"  {svc}: ok")

sys.exit(1 if failed else 0)
PY
  if [ $? -eq 0 ]; then
    mark_pass "6 Dockerfiles valid"
  else
    mark_fail "Dockerfile validation"
    cat /tmp/docker.err | sed 's/^/    /'
  fi
}

# ---------------------------------------------------------- workflow YAML

run_workflow_lint() {
  print_header "Workflow YAML lint"
  if ! python3 -c "import yaml" 2>/dev/null; then
    mark_skip "workflow yaml" "PyYAML not installed"
    return
  fi
  ROOT="$(cd "$PROJECT_DIR/.." && pwd)"
  WORKFLOWS_DIR="$ROOT/.github/workflows"
  if [ ! -d "$WORKFLOWS_DIR" ]; then
    mark_skip "workflow yaml" "no .github/workflows dir"
    return
  fi
  FAIL=0
  for f in "$WORKFLOWS_DIR"/*.yml; do
    if python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/tmp/yaml.err; then
      printf "  ${GREEN}·${RESET} %s\n" "$(basename "$f")"
    else
      printf "  ${RED}·${RESET} %s\n" "$(basename "$f")"
      cat /tmp/yaml.err | sed 's/^/      /'
      FAIL=1
    fi
  done
  if [ $FAIL -eq 0 ]; then
    mark_pass "all workflow YAML parses"
  else
    mark_fail "workflow yaml"
  fi
}

# ---------------------------------------------------------------- scoring

print_summary() {
  print_header "Summary"
  local fails=0
  for k in "${!SCORE[@]}"; do
    case "${SCORE[$k]}" in
      pass) printf "  ${GREEN}✓${RESET} %s\n" "$k" ;;
      fail) printf "  ${RED}✗${RESET} %s\n" "$k"; fails=$((fails+1)) ;;
      skip) printf "  ${YELLOW}-${RESET} %s\n" "$k" ;;
    esac
  done | sort
  echo
  if [ $fails -eq 0 ]; then
    printf "${GREEN}${BOLD}All checks passed.${RESET}\n"
    return 0
  else
    printf "${RED}${BOLD}%d check(s) failed.${RESET}\n" "$fails"
    return 1
  fi
}

# ------------------------------------------------------------------- main

MODE="${1:-all}"
case "$MODE" in
  all)
    run_pytest
    run_node_tests
    run_compileall
    run_terraform_fmt
    run_terraform_validate
    run_docker_validate
    run_workflow_lint
    ;;
  tests)
    run_pytest
    run_node_tests
    ;;
  lint)
    run_compileall
    run_terraform_fmt
    ;;
  docker)
    run_docker_validate
    ;;
  terraform)
    run_terraform_fmt
    run_terraform_validate
    ;;
  workflows)
    run_workflow_lint
    ;;
  *)
    echo "usage: $0 [all|tests|lint|docker|terraform|workflows]" >&2
    exit 2
    ;;
esac

print_summary
