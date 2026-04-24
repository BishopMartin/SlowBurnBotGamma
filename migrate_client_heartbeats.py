"""One-shot migration: create client_heartbeats table.

Usage:
    railway service SlowBurnBotGamma
    railway run python migrate_client_heartbeats.py
"""
import asyncio
import os

import asyncpg


async def main():
    url = os.environ["DATABASE_PUBLIC_URL"]
    conn = await asyncpg.connect(url)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS client_heartbeats (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                client_id INTEGER NOT NULL,
                system_type VARCHAR(50) NOT NULL DEFAULT '',
                ip_address VARCHAR(100) NOT NULL DEFAULT '',
                status VARCHAR(50) NOT NULL DEFAULT 'idle',
                current_account TEXT,
                last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_client_heartbeat_user_client UNIQUE (user_id, client_id)
            );
            CREATE INDEX IF NOT EXISTS ix_client_heartbeats_user_id ON client_heartbeats(user_id);
        """)
        print("client_heartbeats table created successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
