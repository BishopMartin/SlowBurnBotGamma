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
- `APP_VERSION` is bumped automatically by pre-push hook — never bump manually
- `BOT_VERSION` in `bot-client/burnBot_version.py` must be incremented with every bot-client change
- Admin account is system-level only — never link to customer-facing pages
- Use `----` for empty/unset fields in UI, `****` for set secrets

## Agent Routing

Default model: `opusplan` (Opus in /plan mode, Sonnet for execution)

| Task | Agent | Model |
|---|---|---|
| Finding files, symbols, configs | `code-searcher` | Haiku |
| Stack traces, Railway logs, errors | `log-analyzer` | Haiku |
| API reference (Stripe, GitHub, Railway) | `docs-lookup` | Haiku |
| Test drafting and QA checklists | `test-drafter` | Sonnet |
| Bug fixes and isolated edits | `implementation-helper` | Sonnet |
| Architecture, migrations, risky changes | `architect-planner` | Opus |

Cost controls:
- Do not spawn more than 2 subagents without asking
- Prefer Haiku agents for read-only search and lookups
- Do not use Opus unless the task is architectural, high-risk, or explicitly `/plan`
- Avoid broad whole-repo scans unless necessary

Safety:
- Haiku agents are read-only (no file edits)
- Only `implementation-helper` may edit files
- `architect-planner` plans only — does not edit by default
- Never modify secrets, credentials, or deployment configs without explicit confirmation
