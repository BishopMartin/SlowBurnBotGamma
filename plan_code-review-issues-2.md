# Code Review Issues — Round 2

Items remaining after the first round of fixes (see `plan_code-review-issues.md` for the original list). Critical and High items in the first review have all shipped; what's left is mostly hardening, cleanup, and gaps that need separate workstreams.

## High

- **Bot client thread-safety holes.**
  `bot-client/burnBot_apiClient.py` is used from multiple threads. Only token read/write is lock-protected; cache fields (`_settings_cache`, `_ignore_cache`, `_config_cache`) are plain in-memory dicts/attributes accessed without synchronization. Latent race risk; needs an audit and per-cache locking or a single instance lock.

- **Bot auth failures are swallowed as empty data.**
  Settings/password/config fetch methods in `burnBot_apiClient.py` use broad `except Exception` and return `None`/empty. A 401 from token expiry currently degrades silently rather than triggering a clear re-auth or surfacing an entitlement failure. Distinguish 401/403 from transport errors and either re-login or stop the run.

- **Real refresh-token flow still missing.**
  `app/routers/auth_refresh.py` carries the `TODO(real-refresh-tokens)` placeholder. The current "refresh" requires a still-valid access token, so an expired token forces a full re-login. Needs a separate long-lived refresh token issued at `/auth/jwt/login`, server-side store/revocation, rotation on use, and bot client refactor.

- **Two sources of truth for "runs today".**
  `bot-client/burnBot_runCounter.py` keeps a local JSON counter while `bot-client/burnBot_accountSession.py` also checks server-side counts via `/bot/run-count`. If they drift (clock skew, file lost, multi-machine), scheduling and enforcement disagree. Pick one — preferably server — and remove the other.

- **Login flow depends on OS focus and keystrokes.**
  `bot-client/burnBot_login.py` uses `pyautogui`/window-activation patterns that target the wrong window in RDP / multi-monitor / focus-race situations. Classic desktop-automation fragility; switch to Selenium element interactions where possible, or guard with an active-window check.

## Medium / Structural

- **Frontend silent `.catch(() => {})` cleanup.**
  Several pages (e.g. `frontend/app/dashboard/config/page.tsx`) swallow fetch failures, leaving "loading forever" or empty-data UI with no error message. Sweep the frontend and route through a shared error surface.

- **CSV export bypasses the shared `request()` helper.**
  `frontend/lib/api.ts` downloads exports with raw `fetch`, so 401 handling and error shape checks differ from the rest of the app. Route exports through `request()` (or a streaming variant of it).

- **Frontend renders FastAPI validation errors poorly.**
  `frontend/lib/api.ts` assumes `detail` is a string, but FastAPI sends structured arrays for `RequestValidationError`. Render those properly so users see what field failed.

- **Bot-ingested text fields are weakly bounded.**
  Schemas in `app/schemas/bot.py` (`SessionLogCreate`, `ActivityLogCreate`) accept `error_message`, `details`, etc. with no length cap. Storage/abuse risk; add `max_length` constraints.

- **Bot client has too many broad `except` paths.**
  General overlap with the auth-failure item above but broader: multiple bot files swallow exceptions or use very broad handlers, which hides real failures in production. Tighten to the specific exception types each call site can raise.

- **Inconsistent / fail-open utility defaults.**
  From the original bot audit: differing debug defaults between modules, schedule parsing that can fail open, `RunCounter` file path depending on CWD. Consolidate paths via `burnBot_config.resolve_path()` and tighten parsing.

- **Migrations run inline in `Dockerfile` startup.**
  `alembic upgrade head` happens at container start. A bad migration or DB lock becomes an immediate availability outage. Move to a pre-deploy step (Railway release command or equivalent) so app boot is independent of migration health.

- **Repo hygiene: environment-specific data in scripts.**
  `scripts/import_xlsx.py` has hard-coded user/environment values. Parameterize or move to a local-only file.

- **No automated test coverage on highest-risk flows.**
  Auth, billing, webhooks, entitlement, migrations, and proxy behavior have no tests. `frontend/package.json` has no `test` script. This is the biggest force multiplier on every other item — separate workstream to set up pytest + a frontend test runner and seed coverage starting with auth/webhooks.

## Notes

- All four Critical items and most High items from `plan_code-review-issues.md` are resolved (notification secrets, trial entitlement, plan-tier consistency, Chrome-kill indent, invite-code race, heartbeats Alembic, admin Stripe timestamps, follow-target vocabulary, account settings save guard, JWT refresh wording cleanup, webhook idempotency + `invoice.payment_succeeded`, proxy header allowlists, INI plaintext creds → keyring).
- Items above are primarily *hardening* and *operational maturity* rather than correctness bugs in the live paths.
