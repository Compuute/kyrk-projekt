#!/usr/bin/env bash
# Cut a release THROUGH a PR (never a direct push to main): bump package.json
# on a release branch and open the PR. After it is squash-merged, tag the
# resulting main commit (the script prints the exact command).
#
# Why a PR: the version bump then runs through CI and is auditable, same as
# every other change. Released tags are immutable (AI-RULES.md RULE 3); a
# correction ships as the next version, never by moving a tag.
#
# Usage: scripts/release.sh 0.2.0
set -euo pipefail

VERSION="${1:-}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "usage: scripts/release.sh X.Y.Z   (e.g. 0.2.0, no 'v' prefix)" >&2
  exit 2
fi
TAG="v$VERSION"
BRANCH="release/$TAG"

cd "$(git rev-parse --show-toplevel)"

if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  echo "tag $TAG already exists on origin — releases are immutable, pick the next version" >&2
  exit 1
fi

# Build the release commit on a fresh branch off the latest origin/main —
# never on main directly.
git fetch -q origin main
git switch -c "$BRANCH" origin/main

node -e '
  const fs=require("fs"), p="package.json";
  const j=JSON.parse(fs.readFileSync(p,"utf8"));
  j.version=process.argv[1];
  fs.writeFileSync(p, JSON.stringify(j,null,2)+"\n");
' "$VERSION"

git add package.json
git commit -q -m "chore(release): $TAG"
echo "committer: $(git log -1 --format='%cn <%ce>')"   # must be the human (RULE 4)

git push -u origin "$BRANCH"
gh pr create --base main --head "$BRANCH" \
  --title "chore(release): $TAG" \
  --body "Version bump to \`$TAG\`. Squash-merge, then tag origin/main (see below)."

cat <<EOF

PR opened. After it is squash-merged and CI is green, tag the merged commit:

  git fetch origin main
  git tag -a $TAG origin/main -m "$TAG"
  git push origin $TAG

The tag then points at the exact main commit that carries the bump.
EOF
