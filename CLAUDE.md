# SlowBurnBot Gamma — Claude Code Guide

## Project overview

FastAPI + PostgreSQL SaaS backend migrating SlowBurnBot off Google Sheets. The compiled Windows exe (`burnBot.exe`) authenticates against this API via JWT; the API owns all data and subscription enforcement.

Architecture: `User exe → FastAPI (Railway) → PostgreSQL`

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + fastapi-users 13 |
| ORM | SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Auth | JWT (Bearer), fastapi-users |
| Billing | Stripe subscriptions + webhooks |
| DB driver | asyncpg |
| Hosting | Railway (API + Postgres) |
| Frontend | Next.js (Phase 4, separate repo) |

## Local development

```bash
# 1. Copy and fill env
cp .env.example .env

# 2. Install deps
pip install -r requirements.txt

# 3. Run migrations (requires DATABASE_URL in .env)
alembic upgrade head

# 4. Start dev server
uvicorn app.main:app --reload --port 8080
```

API docs at `http://localhost:8080/docs` (dev/staging only; disabled in production).

## Common commands

```bash
# New migration after model changes
alembic revision --autogenerate -m "describe change"
alembic upgrade head

# Run with Docker
docker build -t slowburnbot-gamma .
docker run --env-file .env -p 8080:8080 slowburnbot-gamma
```

## Project layout

```
app/
  main.py          — FastAPI app, middleware, router registration
  settings.py      — Pydantic-settings (reads .env)
  database.py      — Async engine, session maker, Base
  auth.py          — fastapi-users setup, JWT strategy, UserManager
  deps.py          — Shared dependencies (subscription checks)
  models/          — SQLAlchemy ORM models
  routers/
    accounts.py    — Dashboard CRUD for bot accounts + settings
    bot.py         — Exe-facing endpoints (entitlement, settings, logs)
    admin.py       — Superuser admin endpoints
    webhooks.py    — Stripe webhook handler
  schemas/         — Pydantic request/response schemas
alembic/           — Migrations; versions/ holds migration files
```

## Key env vars

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | asyncpg connection string (Railway injects `postgresql://`; settings.py auto-converts) |
| `SECRET_KEY` | JWT signing secret — strong random hex |
| `ENVIRONMENT` | `development` / `production` (disables /docs in production) |
| `STRIPE_SECRET_KEY` | Stripe secret key (Phase 3+) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `CORS_ORIGINS` | JSON list of allowed frontend origins |

## Auth flow

- `POST /auth/jwt/login` → Bearer token (1 h access)
- All protected routes require `Authorization: Bearer <token>`
- Superuser routes use `current_superuser` dependency
- On registration, `UserManager.on_after_register` auto-creates an inactive `free` subscription row

## Subscription / entitlement

- `GET /bot/entitlement` — lite check for exe startup (no subscription = free/inactive)
- `require_active_subscription` dependency gates settings fetch and other paid routes
- Stripe webhooks update the `subscriptions` table; see `routers/webhooks.py`

## Multi-tenancy rule

Every data row is scoped to `user_id`. Account ownership is verified with `_get_owned_account` / `_assert_account_owned` helpers before any read or write.

## Migration plan phases

1. Setup (Railway, Postgres, Stripe, domain)
2. **DB schema** ← current phase
3. FastAPI backend (auth, bot endpoints, Stripe webhooks)
4. Next.js frontend
5. Exe integration (replace Sheets calls with API calls, keyring JWT storage)
6. Deploy + E2E test

See `BurnBotGamma-MigrationPlan.md` for full detail and `BurnBotBeta-ArchitectureOutline.md` for the legacy Sheets system being replaced.
