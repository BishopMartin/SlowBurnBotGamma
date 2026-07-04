"""Add access_tokens table — server-side revocable sessions.

Backs the switch from a stateless signed JWT to fastapi-users' DatabaseStrategy
(app/auth.py): the bearer token is now an opaque string looked up here on
every request, so logout / password-change can actually revoke it instead of
it remaining valid until its natural expiry regardless of what the user does.

Revision ID: w3v8w9x0y1z2
Revises: v2q3r4s5t6u7
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "w3v8w9x0y1z2"
down_revision = "v2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_tokens",
        sa.Column("token", sa.String(43), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_access_tokens_user_id", "access_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_access_tokens_user_id", table_name="access_tokens")
    op.drop_table("access_tokens")
