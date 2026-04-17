#!/usr/bin/env bash
# Deploy both Railway services.
# Requires: railway CLI logged in and linked to the correct project.
# Usage: bash scripts/deploy.sh
set -e

cd "$(dirname "$0")/.."

echo "=== Deploying backend (SlowBurnBotGamma) ==="
railway service SlowBurnBotGamma
railway up --detach --ci

echo ""
echo "=== Deploying frontend (SlowBurnBotFrontend) ==="
railway service SlowBurnBotFrontend
railway redeploy --yes

echo ""
echo "=== Done. Monitor builds at: https://railway.app/dashboard ==="
