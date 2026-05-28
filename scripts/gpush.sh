#!/bin/sh
# gpush.sh — bump APP_VERSION, commit, then push in one clean step.
# Usage: ./scripts/gpush.sh [git push args]
set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if ! git diff --quiet -- frontend/lib/version.ts 2>/dev/null; then
  echo "gpush: frontend/lib/version.ts has unstaged changes — commit or stash first." >&2
  exit 1
fi
if ! git diff --cached --quiet -- frontend/lib/version.ts 2>/dev/null; then
  echo "gpush: frontend/lib/version.ts has staged changes — commit them first." >&2
  exit 1
fi

node scripts/bump-frontend-version.mjs

if ! git diff --quiet -- frontend/lib/version.ts 2>/dev/null; then
  git add frontend/lib/version.ts
  VERSION=$(grep -o '"[0-9.]*"' frontend/lib/version.ts | tr -d '"')
  BOT_VERSION=$(grep -o '"[0-9.]*"' bot-client/burnBot_version.py | tr -d '"')
  git commit -m "chore: bump website to v${VERSION} / client v${BOT_VERSION}" --no-verify
fi

SKIP_VERSION_BUMP=1 git push "$@"
