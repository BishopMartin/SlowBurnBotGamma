#!/usr/bin/env bash
# Deploy both Railway services.
# Requires: railway CLI logged in and linked to the correct project.
# Usage: bash scripts/deploy.sh
#
# Migrations run automatically: SlowBurnBotGamma has a Railway pre-deploy
# command (`alembic upgrade head`) that runs after build, before the new
# version takes traffic. No manual `railway run alembic upgrade head` step
# needed here. (The root Dockerfile's own `alembic upgrade head && uvicorn
# ...` CMD is not the active build path — the service builds via Railpack.)
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
