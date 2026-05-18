#!/usr/bin/env bash
# Push a bot-client release tag and wait for build artifacts before syncing the server.
#
# Usage:
#   bash scripts/release-bot-client.sh
#
# Steps:
#   1. Push bot-client-vX.XXX tag → triggers GitHub Actions (EXE + Docker build, ~3-4 min)
#   2. Polls /admin/sync-bot-version every 20s until both artifacts exist (max 10 min)
#   3. Once artifacts are live, the server advances current_bot_version and the
#      dashboard banner updates.
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
echo "==> Pushed ${TAG} — GitHub Actions build triggered (~3-4 min)."

# Authenticate
echo "==> Authenticating..."
LOGIN_RESP=$(curl -s -X POST "${PUBLIC_API_URL}/auth/jwt/login" \
  -d "username=${ADMIN_EMAIL}&password=${ADMIN_PASSWORD}")
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)
if [ -z "$TOKEN" ]; then
  echo "error: login failed — $(echo "$LOGIN_RESP" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESP")" >&2
  exit 1
fi

# Poll sync endpoint until both artifacts exist (EXE in S3 + Docker image in GHCR)
echo "==> Waiting for build artifacts..."
DEADLINE=$(( $(date +%s) + 600 ))
POLL_INTERVAL=20

while :; do
  HTTP_CODE=$(curl -s -o /tmp/_sync_resp.json -w "%{http_code}" -X POST \
    "${PUBLIC_API_URL}/admin/sync-bot-version" \
    -H "Authorization: Bearer ${TOKEN}")

  if [ "$HTTP_CODE" = "200" ]; then
    UPDATED_TO=$(python3 -c "import json; print(json.load(open('/tmp/_sync_resp.json')).get('updated_to',''))" 2>/dev/null)
    echo "==> Server synced: current_bot_version = ${UPDATED_TO}"
    break
  elif [ "$HTTP_CODE" = "202" ]; then
    STATE=$(python3 -c "
import json
d = json.load(open('/tmp/_sync_resp.json'))
print(f'exe={d.get(\"exe_ready\")} image={d.get(\"image_ready\")}')" 2>/dev/null)
    NOW=$(date +%s)
    if [ "$NOW" -ge "$DEADLINE" ]; then
      echo "error: build did not complete within 10 min (${STATE})" >&2
      exit 1
    fi
    REMAINING=$(( DEADLINE - NOW ))
    echo "  ... build still running (${STATE}); retrying in ${POLL_INTERVAL}s (${REMAINING}s left)"
    sleep "$POLL_INTERVAL"
  else
    echo "error: sync returned HTTP ${HTTP_CODE} — $(cat /tmp/_sync_resp.json)" >&2
    exit 1
  fi
done
