# SlowBurnBot Beta — Architecture Outline

Source tree: **`C:\DevProjects\SlowBurnBot\SlowBurnBotBeta`** (Python client; Google Sheets + Selenium). This document summarizes how it works today to inform the Gamma / SaaS migration (API + Postgres replacing Sheets).

---

## 1. High-level purpose

A **multi-account, scheduled automation client** that:

- Reads **per-account settings and schedules** from a **Google Sheet** (main “data” workbook).
- Runs **browser automation** (Selenium + Chrome) per account, with optional **reuse** of Chrome sessions.
- Writes **structured session logs**, **errors**, and optional **activity** rows to Sheets.
- Sends optional **admin notifications** (email / SMS), with some credentials loaded from a **separate config spreadsheet**.

---

## 2. Entry point and control flow

| Component | Role |
|-----------|------|
| **`burnBot.py`** | Loads **`burnBot_config.ini`** (path overridable via `sys.argv[1]`), instantiates **`DriveManager`**, then runs an infinite **main loop**: refresh a **slice** of the settings tab (`get_settings_rows`, e.g. A3:AO, up to 200 rows), rebuild **enabled accounts** (sheet status + **`system_group`** filter), maintain **schedules**, **next run times**, and **`RunCounter`** (local JSON), spawn **`burnBot_accountSession`** threads when an account is due, coordinate shutdown via **`threading.Event`** and keyboard interrupt. |
| **`burnBot_accountSession.py`** | Per-account worker: parses **`row_values`** from the settings row (password, schedule, up to four actions, unfollow days, topics), creates or reuses **Chrome** via **`create_driver`**, **`handle_account_login`**, executes configured modules, calls **`driveManager.log_session_run`** / **`log_error`**, optional notifications. |
| **`burnBot_accountSession_setup.py`** | Chrome/Selenium wiring: **`system_type`** in INI selects **`[driver.uchrome.windows]`** vs **`[driver.uchrome.chromebook]`**; per-account profile under **`chrome_user_data_dir_base`** (e.g. `PortableChrome\user_{account}`); remote debugging port assignment; **`is_bot_debug_enabled()`**. |
| **`burnBot_runCounter.py`** | Persists **`burnBot_runs.json`**: per-account **today’s run count** and **last run ISO timestamp** for scheduling in the main loop. |

---

## 3. Configuration layers

1. **Local INI** — **`burnBot_config.ini`**: `[bot_settings]`, `[session_settings]`, `[notifications]`, `[drive]`, `[driver.uchrome.*]`.
2. **Remote “data” spreadsheet** — Service account JSON path in INI; workbook name + tab names for **settings**, **ignore**, **runlog**.
3. **Optional remote “config” spreadsheet** — Separate workbook/tab (e.g. `BurnBot - config` / `settings`) with **A = variable name**, **B = value** for notification credentials (`burnBot_driveManager.get_config_value`).

---

## 4. Google Sheets integration (`burnBot_driveManager.py`)

- **Library:** **`pygsheets`**, authorized with **service account** JSON (`driveDataService` in INI).
- **Main workbook** (`driveDataFile`):
  - **Settings worksheet** — Partial matrix reads with short TTL cache (`get_settings_rows`); full records cache (`get_all_records`) for **`get_account_settings`**. **`update_account_status(account, field, value)`** updates a cell by **header row** + account in column A (implemented; **not referenced** by other modules in a repo-wide search — still part of the intended data model).
  - **Runlog worksheet** (`driveDataLogTab`, e.g. `runlog`) — **`log_session_run`**: inserts a structured row (newest near top), tracks **in-memory run counts** per account/day, can **seed** count from existing sheet rows after restart; optional **day-separator** border formatting.
  - **`log_activity`** / **`log_error`** — Append timestamped rows to the log tab.
  - **Ignore worksheet** (optional) — **Column A**: ignore/block list consumed by like/follow/unfollow flows.
- **Per-account worksheets** — Opened elsewhere by **worksheet title = account name** (see §6).

---

## 5. Settings row layout (as implemented in code)

Main loop and session use a row matrix up to **column AO** (0-based indices in `burnBot_accountSession.py` / `burnBot.py`):

| Index | Column (approx.) | Meaning |
|-------|-------------------|---------|
| 0 | A | Account identifier |
| 1 | B | Enabled (`TRUE` / `1` / `YES` / `ON`, etc.) |
| 2 | C | Group (filtered against `system_group` in INI) |
| 3 | D | Password (session login) |
| 9–14 | J–O | Schedule: days, (spare), start, end, delay (`60` or `60/10`), max runs/day |
| 15–19 | P–T | Action 1: enable, type, target, fixed count, variable count |
| 20–24 | U–Y | Action 2 |
| 25–29 | Z–AD | Action 3 |
| 30–34 | AE–AI | Action 4 |
| 35 | AJ | Unfollow days (default 30) |
| 40 | AO | Topics string (topic-like flows) |

**User agent** for the browser is taken from **local INI** (`system_user_agent`), not from the sheet.

---

## 6. Feature modules

| Module | Notes |
|--------|--------|
| **`burnBot_login.py`** | Account login; receives **`driveManager`** for logging paths used by session. |
| **`burnBot_likePostsHome.py`**, **`burnBot_likePostsTopic.py`** | Home/topic likes; optional **`ignore_tab`** column A. |
| **`burnBot_followSuggested.py`**, **`burnBot_followGroup.py`** | Open **`driveManager.file`** worksheet **by title = account**; may read universal ignore list from **`ignore_tab`**. |
| **`burnBot_unfollowDatabase.py`** | Per-account worksheet titled **`account`**. |
| **`burnBot_randomActions.py`** | Randomized behavior invoked from the session. |
| **`burnBot_notifications.py`** | Uses INI `admin_*`; reads **SMTP / Textbelt** from **config sheet** when `config_tab` is available. |
| **`burnBot_utils.py`** | Retries, schedule window checks, connectivity helpers, etc. |

---

## 7. Dependencies and runtime (from code)

- **Selenium 4**, **webdriver_manager**, **pygsheets**, **pandas**, **requests**, **psutil**, standard library (threading, `configparser`, etc.).
- **Windows:** bundled **`PortableChrome\chrome.exe`** and profiles under repo (large tree; distribution/.gitignore concern).
- No **`requirements.txt`** was present in Beta root at the time of this outline; infer deps from **`burnBot_imports.py`** and each module.

---

## 8. Migration API surfaces (Gamma / FastAPI mapping)

These are the natural boundaries to replace with authenticated HTTP + Postgres:

1. **Settings row / matrix** — Equivalent to **`account_settings`** (+ tenant **`user_id`**); replaces settings tab reads and optional **`update_account_status`** / **`get_account_settings`**.
2. **Structured session log** — **`log_session_run`** row shape (date, sequence, times, account, four action aggregates, error).
3. **Fine-grained activity / errors** — **`log_activity`**, **`log_error`** (or merge into a single **`logs`** stream with a `kind` field).
4. **Global ignore list** — Ignore tab column A → shared or per-user resource.
5. **Per-account named tabs** — Follow/unfollow “databases” keyed by account → **`accounts`**-scoped tables or documents.
6. **Notification secrets** — Today in config sheet → **never in the exe**; server-side secrets, env, or user-provided integrations in the dashboard.

**Security note for schema design:** Sheet column **D** holds **passwords** in plaintext today; the hosted model should use **OAuth where possible**, **server-side encryption**, or **client-held secrets** with clear threat modeling—not a straight copy of the sheet column into a public API field.

---

## 9. Related planning doc

See **`BurnBotGamma-MigrationPlan.md`** in this repo for phased delivery, prerequisites, and SaaS stack decisions.

---

*Generated from static review of SlowBurnBotBeta Python sources; refresh if Beta diverges.*
