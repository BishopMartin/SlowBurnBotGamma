# SlowBurnBot — SaaS Migration Plan

This document captures the migration from Google Sheets to a hosted stack (Railway, FastAPI, Next.js, PostgreSQL, Stripe) plus refinements from planning review. Use it while mapping requirements **before** writing production code.

---

## 1. Prerequisites — gather before development

Collect accounts, access, and decisions below so setup (Phase 1) and local development are not blocked. Store secrets only in password managers or platform secret stores—never in the repo.

### Hosting and runtime

| Item | Purpose | Notes |
|------|---------|--------|
| **Railway account** | Deploy API, optional worker, Postgres | Decide team/org billing owner |
| **GitHub (or Git) remote** | Source + auto-deploy from `main` / tags | Connect repo to Railway |
| **Domain registrar + DNS** | Public URLs, SSL | Point DNS to Railway; ~$12/yr typical |
| **Environment matrix** | `local`, `staging` (optional), `production` | Separate Railway projects or services per env if desired |

### Database

| Item | Purpose |
|------|---------|
| **PostgreSQL** | Managed instance on Railway (or chosen host) |
| **Connection string** | `DATABASE_URL` for API and Alembic (SSL params as required by host) |
| **Backup / restore expectation** | Who runs restores; RPO/RTO (even informal) |

### Payments (Stripe)

| Item | Purpose |
|------|---------|
| **Stripe account** | Live + Test modes |
| **Test API keys** | `sk_test_…`, `pk_test_…` for local and staging |
| **Live API keys** | Only in production secrets (when ready) |
| **Webhook signing secret** | Per endpoint URL (`whsec_…`) |
| **Products and Prices** | Subscription tiers; Price IDs for app config |
| **Customer Portal** | Enabled in Stripe Dashboard for self-serve billing |
| **Tax / business address** | If charging VAT/sales tax (Stripe Tax optional) |

### Auth and security (to decide or provision)

| Item | Purpose |
|------|---------|
| **JWT signing secret** | Strong random secret for FastAPI-Users / auth |
| **CORS allowed origins** | Production Next.js URL(s) |
| **Admin bootstrap** | First admin user creation strategy (seed script vs invite) |

### Email (if required for FastAPI-Users or flows)

| Item | Purpose |
|------|---------|
| **Transactional email provider** | Resend, SendGrid, etc., if verification/reset emails are used |
| **From domain / DNS records** | SPF, DKIM as required by provider |

### Desktop executable (Phase 5+)

| Item | Purpose |
|------|---------|
| **Code signing certificate** (recommended before wide distribution) | Reduces Windows SmartScreen warnings |
| **Build machine / CI** | Where PyInstaller builds run |
| **Update policy** | How users get new `.exe` versions |

### Product / legal (often parallel to engineering)

| Item | Purpose |
|------|---------|
| **Privacy policy + Terms URLs** | Stripe, dashboard, signup |
| **Support contact** | For billing and access issues |

### Technical inputs for schema and API design

| Item | Purpose |
|------|---------|
| **Current Google Sheets structure** | Tab names, columns, read/write patterns |
| **Account vs user semantics** | One user → many bots/accounts? naming (`bot_accounts` vs `accounts`) |
| **Log volume estimate** | Events per day per user; drives retention and batching |
| **Entitlement rules** | What “active subscription” means for API vs bot startup |

---

## 2. Goal

Move SlowBurnBot off Google Sheets for data storage and build SaaS infrastructure with user accounts, a web dashboard, admin controls, and subscription billing.

---

## 3. Final platform stack

```
Railway
├── FastAPI backend (API + auth + business logic)
├── Next.js frontend (user dashboard + admin panel)
└── PostgreSQL (managed database)
```

| Concern | Choice |
|---------|--------|
| Billing | Stripe (subscriptions) |
| Windows client | PyInstaller → `.exe` |
| Local token storage | Windows **keyring** for JWT material |
| Domain | Purchased separately; DNS to Railway |

**Rough cost at zero users:** ~$11/mo (hosting + domain; Stripe has no revenue until customers pay).

---

## 4. Key architectural decision

The compiled executable **must not** contain database credentials. All database access goes through the API:

```text
User's exe → FastAPI (Railway) → PostgreSQL
```

The exe authenticates with **JWT** (stored via keyring). The API enforces access control, tenancy (per user / per account), and **subscription entitlement**.

---

## 5. Database tables (initial sketch)

| Table | Role |
|-------|------|
| `profiles` | Extended user data; link 1:1 to auth user (`user_id` FK); plan tier / display fields—avoid duplicating email unless source of truth is explicit |
| `subscriptions` | Stripe subscription id, status, billing period, customer id |
| `accounts` | Bot accounts each user manages (consider rename to `bot_accounts` if “account” collides with billing language) |
| `account_settings` | Per-account configuration (replaces Sheets) |
| `logs` | Activity / session data (replaces Sheets); plan retention, indexing, and optional batching |

Implementation: **SQLAlchemy models** + **Alembic** migrations. Access control in **FastAPI** (and optional Postgres RLS later).

---

## 6. Entitlement and Stripe (planning additions)

- **Stripe** is source of truth for payment state; the app maintains **derived entitlement** (e.g. active flag, tier, `current_period_end`, grace if you add it).
- **Webhooks:** verify signatures; implement **idempotency** (same `event.id` processed once); tolerate retries and out-of-order delivery.
- **API behavior:** sensitive routes should check entitlement (not only “bot checked once at startup”), so a missed webhook does not strand paid users indefinitely.
- **Admin / ops:** consider a manual “sync subscription from Stripe” for support.

---

## 7. JWT and desktop client (planning additions)

- Prefer **short-lived access tokens** and a **refresh** flow (or periodic re-login) to limit damage from token leakage. Keyring reduces casual loss but does not stop a compromised machine.
- Rate-limit auth and log-ingest endpoints appropriate for the exe.

---

## 8. Logs and scale (planning additions)

- Estimate write rate; prefer **batched** log posts from the exe if volume is high.
- Define **retention** (delete after N days, or archive to object storage later).
- Index by `(user_id, account_id, created_at)` (adjust to real query patterns).

---

## 9. Multi-tenancy rules

- Decide: one user, many `accounts` / bots—yes or no.
- Every row that belongs to a bot should be queryable only with **`user_id` + `account_id`** (or equivalent) enforced in the service layer.

---

## 10. Phased delivery

### Phase 1 — Setup (manual, ~30 min)

- Railway account + PostgreSQL provisioned  
- GitHub repo connected for auto-deploy  
- Domain purchased and pointed to Railway  
- Stripe account created; test keys and webhook endpoint URL reserved  

### Phase 2 — Database schema

- SQLAlchemy models aligned with current Sheets **and** entitlement/subscription fields  
- Alembic migrations from day one  
- Access control designed in FastAPI (document rules in code or short ADR)  

### Phase 3 — FastAPI backend

- FastAPI-Users: registration, login, JWT, admin vs user roles  
- Endpoints for exe: settings, logging, subscription validation  
- Stripe webhook handler: updates `subscriptions` / entitlement  
- Admin-only endpoints for control panel  
- Webhook idempotency + optional admin sync  

### Phase 4 — Next.js frontend

- Login / signup  
- User dashboard: account status, settings, activity logs  
- Admin: users, plans, manual overrides, Stripe sync (if built)  
- Billing: Stripe Customer Portal  

### Phase 5 — Executable integration

- Replace all Sheets calls with FastAPI calls  
- Login: receive tokens; store via keyring  
- Subscription / entitlement check on startup and on critical paths  
- PyInstaller build; plan code signing and distribution  

### Phase 6 — Deploy and test

- Set env vars in Railway  
- E2E: signup → payment (test mode) → webhook updates state → bot connects → logs visible in dashboard  
- Verify webhook failure / retry behavior in staging  

---

## 11. Next working session (before coding)

1. Open the bot source and document **Sheets read/write**: tabs, columns, types, frequency.  
2. Document the **in-memory / domain model** for accounts and settings as used today.  
3. Confirm **user ↔ many bots** product rule and final table naming (`accounts` vs `bot_accounts`).  
4. That output feeds **Phase 2** ERD and the **FastAPI** project scaffold.

---

## 12. Security baseline (checklist)

- HTTPS only in production  
- CORS restricted to known frontend origins  
- Stripe webhook **signature verification**  
- No secrets in git; Railway (and local `.env` not committed) only  
- Rate limiting on login and high-volume exe endpoints  

---

*Last updated: planning pass — content merges original migration summary with pre-build prerequisites and review refinements.*
