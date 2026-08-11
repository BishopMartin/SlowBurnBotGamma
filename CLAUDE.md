# SlowBurnBotGamma

## Project Overview

Full-stack bot management platform:
- **Backend:** FastAPI + SQLAlchemy 2.0 async + Alembic migrations, PostgreSQL on Railway
- **Frontend:** Next.js (App Router), deployed on Railway
- **Bot client:** Python (`bot-client/`), versioned via `bot-client/burnBot_version.py`
- **Billing:** Stripe subscriptions, three tiers: crawl / walk / run
- **CI/CD:** GitHub Actions for bot build dispatch and artifact download
- **Deployment:** Railway (backend service + frontend service + PostgreSQL)

Key conventions:
- `APP_VERSION` is bumped by `scripts/gpush.sh` — use it in place of `git push` (it bumps, commits, then pushes with the bump skipped on that push); never bump manually. `githooks/pre-push` is a no-op stub that just points to `gpush.sh`.
- `BOT_VERSION` in `bot-client/burnBot_version.py` must be incremented with every bot-client change
- Admin account is system-level only — never link to customer-facing pages
- Use `----` for empty/unset fields in UI, `****` for set secrets

## Pointers

- Frontend has its own scoped doc: `frontend/AGENTS.md`
- Railway + GitHub plugins are enabled in `.claude/settings.json`
- Deploy/release scripts live in `scripts/` (`deploy.sh`, `release-bot-client.sh`, `bump-frontend-version.mjs`)
- Never modify secrets, credentials, or deployment configs without explicit confirmation
