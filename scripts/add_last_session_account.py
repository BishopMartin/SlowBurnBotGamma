"""Add last_session_account column to client_heartbeats."""
import asyncio
import os
import asyncpg


async def main():
    url = os.environ["DATABASE_PUBLIC_URL"]
    conn = await asyncpg.connect(url)
    try:
        await conn.execute("""
            ALTER TABLE client_heartbeats
            ADD COLUMN IF NOT EXISTS last_session_account TEXT
        """)
        print("ok: last_session_account column added (or already existed)")
    finally:
        await conn.close()


asyncio.run(main())
