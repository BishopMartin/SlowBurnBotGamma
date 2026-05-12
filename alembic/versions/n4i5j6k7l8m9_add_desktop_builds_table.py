"""Add desktop_builds table.

Revision ID: n4i5j6k7l8m9
Revises: m3h4i5j6k7l8
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "n4i5j6k7l8m9"
down_revision = "m3h4i5j6k7l8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "desktop_builds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("build_options", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("github_run_id", sa.String(64), nullable=True),
        sa.Column("artifact_name", sa.String(200), nullable=True),
        sa.Column("artifact_sha256", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("activation_token_hash", sa.String(64), nullable=False),
        sa.Column(
            "activation_token_expires_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("download_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_downloads", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "client_id", name="uq_desktop_build_user_client"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "ix_desktop_builds_user_id",
        "desktop_builds",
        ["user_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_desktop_builds_user_created",
        "desktop_builds",
        ["user_id", "created_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_desktop_builds_github_run_id",
        "desktop_builds",
        ["github_run_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("desktop_builds")
