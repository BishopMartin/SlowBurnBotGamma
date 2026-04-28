"""One-shot migration: add actions_random_order column to account_settings table."""
import os
import psycopg2


def main():
    url = os.environ["DATABASE_PUBLIC_URL"]
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE account_settings
            ADD COLUMN IF NOT EXISTS actions_random_order BOOLEAN DEFAULT FALSE
        """)
        print("account_settings.actions_random_order column: OK")
    finally:
        cur.close()
        conn.close()
    print("Done.")


main()
