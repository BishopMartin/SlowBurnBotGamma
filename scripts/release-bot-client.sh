#!/usr/bin/env bash
# Push a bot-client release tag and sync the server's bot version in one step.
#
# Usage:
#   bash scripts/release-bot-client.sh
#
# Reads BOT_VERSION from bot-client/burnBot_version.py, creates + pushes the
# matching tag, then hits the admin sync endpoint so the server picks up the
# new version immediately (no redeploy required).
#
# Requires ADMIN_EMAIL and ADMIN_PASSWORD to be set — either exported in the
# shell or stored in a .env file at the repo root.
# PUBLIC_API_URL defaults to the production Railway URL if not set.

set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Source .env for ADMIN_EMAIL, ADMIN_PASSWORD, PUBLIC_API_URL if present
if [ -f .env ]; then
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

PUBLIC_API_URL="${PUBLIC_API_URL:-https://slowburnbotgamma-production.up.railway.app}"

if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
  echo "error: ADMIN_EMAIL and ADMIN_PASSWORD must be set (in .env or environment)." >&2
  exit 1
fi

BOT_VERSION=$(python3 -c "
import re, sys
m = re.search(r'BOT_VERSION\s*=\s*[\"\']([\d.]+)[\"\']', open('bot-client/burnBot_version.py').read())
print(m.group(1) if m else sys.exit(1))
")
TAG="bot-client-v${BOT_VERSION}"

echo "==> Bot version: ${BOT_VERSION}"

# Create tag if it doesn't exist locally
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "==> Tag ${TAG} already exists locally."
else
  git tag "$TAG"
  echo "==> Created tag ${TAG}."
fi

# Push tag (triggers GitHub Actions build)
git push origin "$TAG"
echo "==> Pushed ${TAG} — GitHub Actions build triggered."

# Authenticate and sync server bot version
echo "==> Syncing server bot version..."
TOKEN=$(curl -sf -X POST "${PUBLIC_API_URL}/auth/jwt/login" \
  -d "username=${ADMIN_EMAIL}&password=${ADMIN_PASSWORD}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

RESULT=$(curl -sf -X POST "${PUBLIC_API_URL}/admin/sync-bot-version" \
  -H "Authorization: Bearer ${TOKEN}")

UPDATED_TO=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('updated_to','?'))")
echo "==> Server synced: current_bot_version = ${UPDATED_TO}"
