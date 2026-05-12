"""One-shot migration: add bot_version column to desktop_builds table."""
import os
import psycopg2


def main():
    url = os.environ["DATABASE_PUBLIC_URL"]
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE desktop_builds
            ADD COLUMN IF NOT EXISTS bot_version VARCHAR(50)
        """)
        print("desktop_builds.bot_version column: OK")
    finally:
        cur.close()
        conn.close()
    print("Done.")


main()
