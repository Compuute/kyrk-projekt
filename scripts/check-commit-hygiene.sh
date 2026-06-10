#!/usr/bin/env bash
# ============================================================================
# Commit hygiene check — enforces AI-RULES.md / RULE 4.
# ----------------------------------------------------------------------------
# Fails if any commit in RANGE was authored or committed by an AI coding tool,
# or carries AI attribution in its message. The committer must always be the
# human owner — this is a property enterprise/security buyers evaluate on.
#
# Deliberately SPECIFIC so legitimate automation is NOT blocked:
#   dependabot[bot] and github-actions[bot] pass.
#
# Usage:
#   scripts/check-commit-hygiene.sh [<git-range>]   # default: origin/main..HEAD
# ============================================================================
set -euo pipefail

RANGE="${1:-origin/main..HEAD}"

# Author/committer identities (name OR email) that must never appear.
IDENT_DENY='claude|anthropic\.com|openai|chatgpt|gpt-[0-9]|github-copilot|copilot\[bot\]|\bcodex\b|cursor\.(so|com)|\bdevin\b'
# Markers/trailers left in commit messages by AI coding tools.
MSG_DENY='co-authored-by:[[:space:]]*[^[:space:]]*(claude|anthropic|gpt|copilot)|generated with claude|claude\.ai/code|🤖'

fail=0
while IFS= read -r sha; do
  [ -z "$sha" ] && continue
  meta=$(git show -s --format='%an|%ae|%cn|%ce' "$sha")
  if printf '%s' "$meta" | grep -qiE "$IDENT_DENY"; then
    echo "::error::commit ${sha:0:8} has AI author/committer identity -> $meta"
    fail=1
  fi
  if git show -s --format='%B' "$sha" | grep -qiE "$MSG_DENY"; then
    echo "::error::commit ${sha:0:8} has AI attribution in its message"
    fail=1
  fi
done <<EOF
$(git rev-list "$RANGE" 2>/dev/null || true)
EOF

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "Commit hygiene check FAILED."
  echo "AI-RULES.md RULE 4: the committer/author must be the human owner, never an AI tool."
  exit 1
fi
echo "Commit hygiene OK for range: $RANGE"
