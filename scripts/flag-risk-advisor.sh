#!/usr/bin/env bash
# Advises (never blocks) whether a change should sit behind a feature flag,
# based on which paths it touches. Human decides; this just surfaces the risk —
# the pattern Netflix/Google use (policy-as-code, not auto-gating).
#
# Reads changed file paths on stdin (one per line). Prints advisory markdown to
# stdout, or nothing if no advice is warranted.
set -euo pipefail

FILES=()
while IFS= read -r line; do FILES+=("$line"); done
[ "${#FILES[@]}" -eq 0 ] && exit 0

# High blast-radius: edge middleware, vendor/auth/payment adapters, routes,
# user-facing pages, data models, donation/intake flows.
HIGH='^functions/|^services/[^/]+/app/(adapters|api)/|^frontend/member-portal/src/pages/|/models\.py$|donate|intake|swish'
# Never advise on these (cosmetic / non-shipping / the flag system itself).
LOW='\.md$|^docs/|/tests?/|\.test\.|styles\.css$|^\.github/|flags\.json$|flags-(eval|hygiene)\.js$'

risky=()
flag_touched=0
for f in "${FILES[@]}"; do
  [ -z "$f" ] && continue
  [[ "$f" =~ flags\.json$ ]] && flag_touched=1
  [[ "$f" =~ $LOW ]] && continue
  [[ "$f" =~ $HIGH ]] && risky+=("$f")
done

# If the PR already touches the flag registry, assume the dev considered it.
{ [ "$flag_touched" -eq 1 ] || [ "${#risky[@]}" -eq 0 ]; } && exit 0

{
  echo "<!-- flag-advisor -->"
  echo "### 🚩 Consider a feature flag"
  echo
  echo "This PR changes high-blast-radius areas. At our scale a bad release reaches everyone at once — consider gating the risky part behind a flag and ramping it (see [docs/27-feature-flag-workflow.md](docs/27-feature-flag-workflow.md))."
  echo
  echo "**Higher-risk files touched:**"
  for f in "${risky[@]}"; do echo "- \`$f\`"; done
  echo
  echo "_Advisory only — not a blocker. If a flag does not fit (trivial/cosmetic/no behaviour change), ignore this._"
}
