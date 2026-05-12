# SlowBurnBot

**Grow your Instagram presence — slowly, safely, and on autopilot.**

SlowBurnBot is a paced, safety-first Instagram automation platform for people who manage more than one account. Instead of hammering Instagram with bursts of activity that get accounts flagged, SlowBurnBot mimics natural human behavior — randomized timing, scheduled active hours, daily caps, and chained activities that look like a real person scrolling. You configure it once in a clean web dashboard; it runs quietly in the background and reports back what it did.

It's built for small businesses, agencies, and creators juggling 3–25 Instagram accounts who want consistent organic growth without the burnout (or bans) of doing it manually. Each account gets its own isolated browser profile, its own schedule, and its own action mix. You see everything — runs, follow-backs, errors, queue state — in one place.

---

## Highlights

- **Multi-account automation** with fully isolated Chrome profiles per account
- **"Slow burn" pacing** — randomized 6–20 second delays, random idle actions between slots, configurable jitter
- **Up to 4 chained action slots per session** — mix likes, follows, and unfollows however you want
- **Schedule-based runs** — pick days of the week, time windows, and a daily run cap
- **Real-time dashboard** with live client heartbeat, activity logs, and follow-back stats
- **Email + SMS alerts** for session completion and login issues
- **Three subscription tiers** — Crawl / Walk / Run, supporting 3 / 10 / 25 accounts
- **CSV data export** — download a per-account spreadsheet of every follow target, with status, dates, and follow-back results
- **Built-in safety toggles** — skip private accounts, skip sponsored posts, global ignore list, 2FA detection

---

## Full Feature List

### Bot Automation Capabilities

- **Like posts** from your home feed (timeline)
- **Like posts** from hashtag/topic searches — comma-separated topic lists (e.g. `beer, craft beer, brewing`)
- **Follow** from Instagram's Explore/People suggestions, with fallback to the home "Suggested for you" carousel
- **Follow** from any public account's followers list or following list (multi-account source lists with random selection)
- **Unfollow** previously followed accounts after a configurable age (default 30 days), tracked in the bot's own follow database
- **Per-slot targeting**: each of the 4 action slots picks its own action type, source, fixed count, and random jitter count
- **Resilient element finding** — multiple selector fallbacks, modal cleanup, stale-element handling for Instagram's shifting UI

### Pacing & Safety

- Randomized 6–20 second delays between every action
- Random "filler" activity (Explore browsing, Reels viewing) between action slots to break up patterns
- Global ignore list — bulk handle list applied across all accounts and actions
- Skip-private-accounts toggle (logs and skips private profiles)
- Skip-sponsored-posts toggle (filters promoted content from the home feed)
- 2FA / phone verification detection with graceful handling
- Per-account isolated Chrome profiles — separate cookies, auth, and user agent
- Daily max-runs-per-day enforcement
- Scheduled active windows (e.g. Mon–Fri, 9am–5pm only)
- Connection retry, health checks, and automatic recovery

### Customer Dashboard

- **Overview** — account summary, plan status, client heartbeat, recent activity feed
- **Accounts** — multi-tab list (Settings / Activity / Stats / Database), sortable columns, enable-disable toggles, client group assignment
- **Account Details** — full per-account editor: schedule, delays, 4 action slots, daily limits, follow source lists, unfollow age, topic lists
- **Stats** — follow-back rates, engagement metrics, queue success rates, breakdown by follower source
- **Activity Log** — session-by-session view with timestamps, run sequence, all 4 actions per session, error messages
- **Database** — pending / complete / ignored follow-target counts per account, last-25 completions, one-click CSV export of the full follow-target history
- **Plan** — current tier, account usage, renewal date, upgrade or downgrade
- **Config** — notification rules, global ignore list, retry attempts, session-level toggles

### Notifications

- **Session completion alerts** — email, SMS, or both
- **Login issue alerts** — separate channel and contact info, falls back to session settings if blank
- Customer notification preferences live in `/dashboard/config`
- Admin-managed sending infrastructure (SMTP server + TextBelt SMS API key) lives in `/admin/config`, with all secrets Fernet-encrypted at rest

### Subscriptions & Onboarding

| Tier  | Price     | Accounts |
|-------|-----------|----------|
| Crawl | $19 / mo  | 3        |
| Walk  | $39 / mo  | 10       |
| Run   | $59 / mo  | 25       |

- Account-limit enforcement: when you exceed your plan, the newest accounts are auto-disabled (system-disabled, not user-disabled), and re-enabled automatically when you upgrade
- Subscription states: Active / Inactive / Trialing, backed by Stripe
- Invite-code registration: admin generates a one-time code, optionally emails it, and can attach a 30-day free trial
- Code-required signup keeps the platform tightly controlled while it grows

### Admin Tools

- User management — list all users, set plan tier, activate/deactivate subscriptions, sync Stripe state
- Invite code generator (`/admin/invites`) — generate, email, or revoke codes before use
- System notification credentials (`/admin/config`) — SMTP host/port/user/password and TextBelt SMS key
- Cross-user account audit — view every Instagram account across every user
- Per-account follow-target queue management

---

## Architecture (one-liner each)

- **Frontend** — Next.js dashboard, deployed to Railway
- **Backend** — FastAPI + SQLAlchemy (async) + PostgreSQL, deployed to Railway
- **Bot client** — Python + Selenium WebDriver, distributed as a Windows `.exe`, runs locally on the customer's machine so each account uses a real browser on a real IP
