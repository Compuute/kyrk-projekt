#!/usr/bin/env bash
# Cut a release: bump package.json and create an annotated semver tag.
# Does NOT push — review first, then `git push origin main vX.Y.Z`.
# Released tags are immutable (AI-RULES.md RULE 3); a correction ships as the
# next version, never by moving a tag.
#
# Usage: scripts/release.sh 0.2.0
set -euo pipefail

VERSION="${1:-}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "usage: scripts/release.sh X.Y.Z   (e.g. 0.2.0, no 'v' prefix)" >&2
  exit 2
fi
TAG="v$VERSION"

cd "$(git rev-parse --show-toplevel)"

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "tag $TAG already exists — releases are immutable, pick the next version" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree not clean — commit or stash first" >&2
  exit 1
fi
if [[ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]]; then
  echo "warning: not on main (on $(git rev-parse --abbrev-ref HEAD))" >&2
fi

# Bump package.json version (the only field touched).
node -e '
  const fs=require("fs"), p="package.json";
  const j=JSON.parse(fs.readFileSync(p,"utf8"));
  j.version=process.argv[1];
  fs.writeFileSync(p, JSON.stringify(j,null,2)+"\n");
' "$VERSION"

git add package.json
git commit -q -m "chore(release): $TAG"
git tag -a "$TAG" -m "$TAG"

echo "created commit + annotated tag $TAG"
echo "tagger: $(git log -1 --format='%cn <%ce>')"
echo "review, then: git push origin main $TAG"
