# Google Sheets → schema reference (no secrets)

This document describes the **structure** of the SlowBurnBot workbooks as used today. It intentionally omits **passwords, API keys, handles used as credentials, and live row samples**. For authoritative headers, compare against a local export (gitignored).

Workbooks referenced in `SlowBurnBotBeta` (`burnBot_config.ini`):

| File (conceptual) | Typical local export name | Purpose |
|-------------------|---------------------------|---------|
| Main data workbook | `thistlegroup-data.xlsx` | Settings, runlog, statistics, ignore, per-account DB tabs, lists |
| Config workbook | `BurnBot - config.xlsx` | Key/value secrets and integration settings |

---

## 1. Main data workbook — sheet: `settings`

Data begins at **row 3** (rows 1–2 are human labels + machine headers).

### Row 1 (group labels, merged conceptually)

High-level groups (left to right): account / pass / group; proxy settings; schedule; four action blocks (`1st` … `4th`); follow settings; like/follow/unfollow data sources.

### Row 2 (column keys used for logic and `get_account_settings`)

| Order | Header (as in sheet) | Role |
|------:|----------------------|------|
| 1 | `account` | Bot account id (Instagram handle / internal name) |
| 2 | `on` | Enabled flag |
| 3 | `grp.` | Group number (filtered by `system_group` in local INI) |
| 4 | `pass` | Login password (**sensitive** — do not store plaintext in git) |
| 5 | *(blank)* | Spacer |
| 6 | `on` | Proxy enabled |
| 7 | `proxy type` | e.g. `none` |
| 8 | `proxy login` | |
| 9 | `proxy password` | (**sensitive**) |
| 10 | `days` | Schedule days (e.g. `daily`) |
| 11 | *(blank)* | |
| 12 | `start` | Window start (Excel may show as fraction of day) |
| 13 | `end` | Window end |
| 14 | `delay` | Minutes; optional `base/random` form in bot (e.g. `90/15`) |
| 15 | `daily` | Max runs per day |
| 16–20 | `on`, `action:`, `target:`, `#`, `?` | **Action 1** enable, type, target, fixed count, variable count |
| 21–25 | same pattern | **Action 2** |
| 26–30 | same pattern | **Action 3** |
| 31–35 | same pattern | **Action 4** |
| 36 | `days` | Unfollow-related days (see Beta code: column index 35 in zero-based row array) |
| 37 | *(blank)* | |
| 38 | `list (seperate tab name)` | Named tab for list-based targets |
| 39 | `account group (comma sep. list)` | Comma-separated parent accounts / groups |
| 40 | `account list (tab name)` | Tab name for account list |
| 41 | `topics (comma sep. list)` | Topic strings for `post[topics]` |

**Beta code note:** `burnBot.py` reads the matrix through column **AO** (index 40) for scheduling; `burnBot_accountSession.py` maps indices 9–14, 15–34, 35, 40 to schedule, actions, unfollow days, and topics.

---

## 2. Main data workbook — sheet: `runlog`

Session summary rows. Beta inserts newest block near **row 3** and uses columns **A–Q** for structured session data (`burnBot_driveManager.log_session_run`).

### Row 1–2 (labels)

| Area | Headers (conceptual) |
|------|----------------------|
| Run metadata | `run date`, `count`, `start time`, `end time`, `account` |
| Four actions | `1st` / `act.` through `4th` / `act.` (type + count pairs) |
| Optional stats | `post`, `folers`, `foling` (sheet spelling; may extend) |
| Errors | `Errors` (row 1); column **Q** in code holds `error_message` |

**Types:** Exported Excel often shows dates/times as **serial numbers**; the bot writes human-readable time strings when logging via API.

**Related:** `log_activity` / `log_error` append a **narrower** row (timestamp, account, action, status, details) to the same tab in some setups—confirm whether production uses one combined tab or split tabs.

---

## 3. Main data workbook — sheet: `statistics`

Aggregated metrics per account (exported layout sample):

| Column | Header | Meaning (inferred) |
|--------|--------|--------------------|
| A–B | `accounts` (twice) | Account label / join key |
| C | *(blank)* | |
| D | `pending` | Count |
| E | `complete` | Count |
| F | `total` | Count |
| G | `success` | Count |
| H | `last 25` | Rate or ratio |
| I | `all time` | Rate or ratio |

**Postgres:** Either a materialized summary table updated by a job, or derived views from `follow_targets` / `session_logs` depending on how metrics are defined.

---

## 4. Main data workbook — sheet: `ignore`

| Row | Content |
|-----|---------|
| 1 | Title / description |
| 2 | Column header: `instagram` |
| 3+ | One handle per row |

Used by like/follow flows to skip targets.

---

## 5. Main data workbook — per-account tabs

Each **worksheet title** equals an **account** name from `settings`. Same column pattern (minor header spelling variant `parent/source` vs `parent-source`):

| Column | Header | Meaning |
|--------|--------|---------|
| A | `account` | Target Instagram user |
| B | `parent/source` | Source bucket (e.g. `something[followers]`) |
| C | `status` | e.g. `done`, `pending` |
| D | `follow date` | Excel serial or date |
| E | `unfol. date` | Planned / actual unfollow |
| F | `follow-back` | `yes` / `no` |

Row 1 often includes summary text (counts of following/overdue).

---

## 6. Main data workbook — list tabs (e.g. `list-MainLineBars`)

Single-column list of handles or identifiers (optional header in row 1). Used as follow/like sources per `settings` list / tab name columns.

---

## 7. Main data workbook — `Menu1`

Dropdown helper: pairs of **1st Drop** / **2nd Drop** valid action combinations (e.g. `like` + `post[homepage]`). Not required for Postgres migration unless the UI replicates Sheets data validation.

---

## 8. Main data workbook — `settings-OLD`

Legacy layout preserved for reference; not described here in detail. New system should not depend on it.

---

## 9. Config workbook — sheet: `settings`

Two columns:

| Column A (`Variable`) | Column B (`Value`) |
|-----------------------|--------------------|
| Arbitrary key | String value |

Keys referenced in Beta (`burnBot_notifications.py`):

- `textbelt_key`
- `smtp_server`, `smtp_port`, `smtp_user`, `smtp_password`

**Postgres / SaaS:** These belong in **server-side secrets**, env vars, or an encrypted admin-managed store—not in a committed spreadsheet or client exe.

---

## 10. Proposed Postgres mapping (v1)

Maps Sheets concepts to the migration plan in `BurnBotGamma-MigrationPlan.md`. Names are suggestions; finalize in Alembic models.

| Sheet / area | Suggested tables | Notes |
|--------------|------------------|--------|
| `settings` row | `accounts` + `account_settings` (or single JSON `settings` per account) | Normalize columns 1–41 into typed fields or JSONB; **never** store `pass` in plaintext at rest without encryption strategy |
| `runlog` structured row | `session_logs` | Columns A–Q + `user_id`, `account_id`, `created_at` |
| `log_activity` lines | `activity_logs` | Optional separate stream or `kind` on unified `logs` |
| `ignore` | `ignore_handles` | `user_id` scope (or global template per org) |
| Per-account tab | `follow_targets` (or `social_targets`) | FK to `accounts`; indexes on `(account_id, status)` |
| List tabs | `named_lists` + `named_list_entries` | Slug from tab name; entries ordered |
| `statistics` | `account_statistics` or computed view | If not derived live, define refresh job |
| Config workbook | `integration_secrets` / env | Not replicated as Sheets; Stripe replaces billing side |

**Multi-tenancy:** Every table above (except global enums) should include **`user_id`** (or `org_id`) and enforce scoping in FastAPI.

---

## 11. Related files

- `BurnBotBeta-ArchitectureOutline.md` — how Beta reads/writes these structures in code.
- `BurnBotGamma-MigrationPlan.md` — phased SaaS delivery.

---

*This file is safe to commit. Do not commit `*.xlsx` exports with live data (see repository `.gitignore`).*
