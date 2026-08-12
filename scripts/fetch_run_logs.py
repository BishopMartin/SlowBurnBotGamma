#!/usr/bin/env python3
"""Read-only fetch of remote bot diagnostics (activity_logs) for developer review.

The bot client uploads diagnostics to the backend (see bot-client/burnBot_run_log.py):
  - kind="run_log": full TUI session transcript, uploaded at session end while
    the Debug Logging (bot_debug) flag is on
  - kind="failure": structured failure records with inline page diagnostics

This script SELECTs those records from the production database. It never writes.

Run it through Railway so the DB credential is injected at runtime and never
stored on the dev machine:

    railway run --service SlowBurnBotGamma -- python3 scripts/fetch_run_logs.py

Options:
    --kind run_log|failure|all   record kind to fetch (default: all)
    --hours N                    look-back window (default: 36)
    --account NAME               filter by account name (substring match)
    --summary                    one line per record, no transcript bodies
    --limit N                    max records (default: 20)
"""

import argparse
import os
import sys

import psycopg2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", default="all", choices=["run_log", "failure", "all"])
    ap.add_argument("--hours", type=int, default=36)
    ap.add_argument("--account", default=None)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_PUBLIC_URL not set — run via: railway run --service "
              "SlowBurnBotGamma -- python3 scripts/fetch_run_logs.py", file=sys.stderr)
        return 1

    kinds = ["run_log", "failure"] if args.kind == "all" else [args.kind]
    where = ["al.kind = ANY(%s)", "al.created_at > now() - make_interval(hours => %s)"]
    params = [kinds, args.hours]
    if args.account:
        where.append("a.name ILIKE %s")
        params.append(f"%{args.account}%")
    params.append(args.limit)

    conn = psycopg2.connect(url)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT al.id, a.name, al.kind, al.action, al.status,
                   al.created_at, al.details
            FROM activity_logs al
            JOIN accounts a ON a.id = al.account_id
            WHERE {' AND '.join(where)}
            ORDER BY al.created_at
            LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    print(f"{len(rows)} record(s), kind={args.kind}, last {args.hours}h")
    for rec_id, name, kind, action, status, created, details in rows:
        details = details or ""
        print(f"\n===== [{kind}] account={name} action={action} status={status} "
              f"at={created:%Y-%m-%d %H:%M:%S}Z id={rec_id} ({len(details)} chars)")
        if args.summary:
            first = details.split("\n", 1)[0]
            print(f"  {first[:200]}")
        else:
            print(details)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
