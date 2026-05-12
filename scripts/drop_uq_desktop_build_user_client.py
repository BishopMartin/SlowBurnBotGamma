"""One-shot migration: drop unique constraint on (user_id, client_id) in desktop_builds.

Slot numbers are now reusable — revoke + rebuild should get the same slot.
"""
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
            DROP CONSTRAINT IF EXISTS uq_desktop_build_user_client
        """)
        print("Dropped uq_desktop_build_user_client: OK")
    finally:
        cur.close()
        conn.close()
    print("Done.")


main()
