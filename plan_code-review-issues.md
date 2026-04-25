# Code Review Issues

## Critical Issues

- **Platform-wide notification secrets are exposed to any authenticated user.**  
  `app/routers/bot.py` returns decrypted SMTP and TextBelt credentials from `SystemConfig` to any logged-in user via `/bot/notification-credentials`, and `bot-client/burnBot_apiClient.py` caches them client-side. In a multi-tenant product, that is a direct secret-boundary failure.

- **The free-trial flow appears broken in real use.**  
  `app/auth.py` creates trial subscriptions with status `trialing`, but `app/deps.py` only treats `active` as entitled, and `app/routers/bot.py` reports `active=False` for trial users. Meanwhile `frontend/app/dashboard/plan/page.tsx` treats `trialing` as a healthy state. Result: the UI says trial is valid while key bot/backend paths still reject the user.

- **Subscription tier state is inconsistent and can collapse users to zero allowed accounts.**  
  `app/routers/admin.py` hardcodes `plan_tier = "pro"` on manual activation even though `app/plan_tiers.py` only recognizes `crawl`, `walk`, and `run`. Separately, Stripe webhook updates in `app/routers/webhooks.py` update subscription status/timestamps but do not clearly keep `User.plan_tier` in sync, while account enforcement in `app/routers/accounts.py` and `app/services/plan_enforcement.py` relies on the user tier. That creates several paths where paid users can still behave like free users or get `0` max accounts.

- **The bot startup path may kill Chrome processes even when it should not.**  
  `bot-client/burnBot_accountSession_setup.py` appears to have an indentation/control-flow bug around the debug-port check, causing Chrome cleanup to run on the new-session path even when the port is not actually occupied. That can make startup brittle and destructive.

## High Issues

- **Invite codes can likely be used twice under concurrent registration.**  
  `app/auth.py` validates the invite in one session and only marks it used later in `on_after_register()` in another session. There is no atomic consume/lock step, so two near-simultaneous signups can probably pass validation before either marks the code spent.

- **Fresh deployments can miss the `client_heartbeats` table.**  
  The model exists in `app/models/client_heartbeat.py`, but the table is created by `migrate_client_heartbeats.py` instead of Alembic, while `Dockerfile` only runs `alembic upgrade head` at startup. A clean deploy can therefore boot without a table the app expects.

- **Admin Stripe resync uses a different timestamp shape than the webhook path.**  
  `app/routers/admin.py` assigns `stripe_sub.current_period_end` directly, while `app/routers/webhooks.py` converts Stripe timestamps to timezone-aware datetimes. That mismatch can cause type errors or inconsistent persisted data.

- **Follow-target status vocabulary is inconsistent across the system.**  
  `app/models/follow_target.py` defaults status to `pending`, `app/schemas/bot.py` defaults it to `following`, and `app/routers/accounts.py` counts “pending” items by filtering for `following`. That makes reporting and any downstream logic around follow lifecycle unreliable.

- **The account settings page can overwrite real settings after a failed load.**  
  In `frontend/app/dashboard/accounts/[id]/page.tsx`, settings-load failures are silently ignored, but save still submits local default action rows through `frontend/lib/api.ts`. If the user saves after a failed fetch, real stored actions can be replaced with empty defaults.

- **Bot auth failures are often swallowed and reinterpreted as missing data.**  
  `bot-client/burnBot_apiClient.py` catches broad exceptions in key methods like settings and password fetch. Session expiry or subscription failures can therefore degrade into `None`/empty behavior instead of forcing a clear re-auth or entitlement error path.

- **The JWT “refresh” flow is not a real refresh-token flow.**  
  `app/routers/auth_refresh.py` requires a still-valid access token via `current_active_user`, and `REFRESH_TOKEN_LIFETIME` in `app/auth.py` is unused. The bot in `bot-client/burnBot_apiClient.py` therefore cannot truly recover from an expired token without logging in again.

- **Webhook handling is incomplete and the idempotency claim is misleading.**  
  `app/routers/webhooks.py` says it handles idempotency, but there is no persisted event deduplication. It also lists `invoice.payment_succeeded` as handled but does not actually process it. That makes billing behavior brittle and the implementation/documentation mismatch risky.

- **The Next.js proxy forwards request/response headers too broadly.**  
  `frontend/app/api/[...path]/route.ts` clones almost all incoming headers and returns backend headers unchanged. That is a common hardening gap: cookies and other sensitive or hop-by-hop headers may be forwarded or reflected more broadly than intended.

- **API credentials are stored in plaintext INI on the bot side.**  
  `bot-client/burnBot.py` reads API email/password from config, while only the JWT is stored in keyring. That is a meaningful exposure risk on shared machines, backups, or copied installs.

- **The bot client shares mutable caches and auth state across threads without full synchronization.**  
  `bot-client/burnBot_apiClient.py` is used from multiple threads, but only part of token handling is locked, and caches are plain in-memory dicts/fields. This looks like a latent race-condition source rather than a guaranteed bug, but it is a real reliability risk.

- **The scheduler uses two separate sources of truth for “runs today.”**  
  `bot-client/burnBot_runCounter.py` and `bot-client/burnBot.py` use a local JSON counter, while `bot-client/burnBot_accountSession.py` also checks server-side counts from `app/routers/bot.py`. If those drift, scheduling decisions and enforcement can disagree.

- **The login flow relies on OS-level focus and keystrokes.**  
  `bot-client/burnBot_login.py` uses `pyautogui`/window activation patterns that can target the wrong window in RDP/multi-window/focus-race situations. That is a classic desktop-automation fragility.

## Medium / Structural Issues

- **Error handling across the frontend hides failures as empty or “loading forever” states.**  
  Several pages, including `frontend/app/dashboard/config/page.tsx`, use silent `.catch(() => {})` patterns. That can leave users stuck on loading screens or seeing empty data without any indication the request failed.

- **CSV export bypasses the shared request/auth path.**  
  `frontend/lib/api.ts` downloads exports with raw `fetch` instead of the common `request()` helper, so 401 handling and response-shape checks are less consistent.

- **Frontend API error rendering drops useful validation detail.**  
  `frontend/lib/api.ts` assumes `detail` is a simple string, but FastAPI validation errors are often structured arrays. That can produce poor or misleading user-facing errors.

- **Bot-ingested text fields appear weakly bounded.**  
  Schemas in `app/schemas/bot.py` accept log/error/detail strings without much validation or length control. That is more of an abuse/storage-risk issue than an immediate exploit, but it is still a weakness.

- **The bot client has too many broad `except` / silent-failure paths.**  
  Multiple bot files swallow exceptions or use very broad handlers, which will make production failures harder to diagnose and may hide real state corruption or auth problems.

- **Some utility/debug defaults are inconsistent or fail open.**  
  Examples from the bot audit include differing debug defaults between modules, schedule parsing that can fail open, and a `RunCounter` file path that depends on the current working directory.

- **Operational/deploy behavior is tightly coupled to startup.**  
  `Dockerfile` runs migrations inline before starting the API. That is sometimes acceptable, but it makes bad migrations or DB lock issues an immediate app availability problem.

- **Repo hygiene has a few environment-specific remnants.**  
  `scripts/import_xlsx.py` includes hard-coded environment/user-style data, which is not catastrophic but is poor operational hygiene.

- **There is little to no automated test coverage for the highest-risk flows.**  
  I did not find meaningful backend/frontend test coverage for auth, billing, migrations, entitlement, or proxy behavior, and `frontend/package.json` has no test script. That is a major risk multiplier across everything above.

## Bottom Line

The biggest themes are:

- **Broken trust boundaries**: shared secrets exposed to normal users.
- **Broken entitlement logic**: trials and paid tiers are not represented consistently.
- **State drift**: tier, billing, webhook, and account-limit logic are not using one clean source of truth.
- **Operational fragility**: migrations, bot startup, and thread/error handling all have failure modes that can be hard to diagnose.
