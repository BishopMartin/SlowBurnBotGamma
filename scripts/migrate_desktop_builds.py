"""One-shot migration: create desktop_builds table."""
import os
import psycopg2


def main():
    url = os.environ["DATABASE_PUBLIC_URL"]
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS desktop_builds (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                client_id INTEGER NOT NULL,
                build_options JSONB NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'queued',
                github_run_id VARCHAR(64),
                artifact_name VARCHAR(200),
                artifact_sha256 VARCHAR(64),
                file_size_bytes BIGINT,
                failure_reason TEXT,
                activation_token_hash VARCHAR(64) NOT NULL,
                activation_token_expires_at TIMESTAMPTZ NOT NULL,
                activated_at TIMESTAMPTZ,
                download_expires_at TIMESTAMPTZ NOT NULL,
                download_count INTEGER NOT NULL DEFAULT 0,
                max_downloads INTEGER NOT NULL DEFAULT 10,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_desktop_build_user_client UNIQUE (user_id, client_id)
            )
        """)
        print("desktop_builds table: OK")

        cur.execute("CREATE INDEX IF NOT EXISTS ix_desktop_builds_user_id ON desktop_builds (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_desktop_builds_user_created ON desktop_builds (user_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_desktop_builds_github_run_id ON desktop_builds (github_run_id)")
        print("Indexes: OK")

        cur.execute("INSERT INTO alembic_version (version_num) VALUES ('n4i5j6k7l8m9') ON CONFLICT DO NOTHING")
        print("Alembic version: OK")

    finally:
        cur.close()
        conn.close()
    print("Done.")


main()
