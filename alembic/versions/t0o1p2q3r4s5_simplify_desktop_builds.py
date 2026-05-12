"""simplify desktop_builds: generic binary flow

Revision ID: t0o1p2q3r4s5
Revises: s9n0o1p2q3r4
Create Date: 2026-05-02

Removes per-customer build tracking columns (github_run_id, artifact_name,
artifact_sha256, file_size_bytes, download_expires_at, download_count,
max_downloads). Adds consumed_at for single-use token enforcement.
Normalizes status: ready+activated_at→activated, all others→revoked.
"""
from alembic import op
import sqlalchemy as sa


revision = "t0o1p2q3r4s5"
down_revision = "s9n0o1p2q3r4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalize status values before dropping old enum territory
    op.execute(
        """
        UPDATE desktop_builds
        SET status = CASE
            WHEN status = 'ready' AND activated_at IS NOT NULL THEN 'activated'
            WHEN status = 'activated' THEN 'activated'
            WHEN status = 'pending_activation' THEN 'pending_activation'
            ELSE 'revoked'
        END
        """
    )

    # Add consumed_at (null = not yet consumed; non-null = token spent)
    op.add_column(
        "desktop_builds",
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill consumed_at for already-activated rows
    op.execute(
        "UPDATE desktop_builds SET consumed_at = activated_at WHERE activated_at IS NOT NULL"
    )

    # Make activation_token_hash nullable (nulled out after consumption)
    op.alter_column("desktop_builds", "activation_token_hash", nullable=True)

    # Make activation_token_expires_at nullable (cleared after consumption)
    op.alter_column("desktop_builds", "activation_token_expires_at", nullable=True)

    # Drop per-customer build tracking columns
    for col in (
        "github_run_id",
        "artifact_name",
        "artifact_sha256",
        "file_size_bytes",
        "download_expires_at",
        "download_count",
        "max_downloads",
    ):
        try:
            op.drop_column("desktop_builds", col)
        except Exception:
            pass  # column may not exist on fresh installs


def downgrade() -> None:
    op.add_column("desktop_builds", sa.Column("github_run_id", sa.String(64), nullable=True))
    op.add_column("desktop_builds", sa.Column("artifact_name", sa.String(200), nullable=True))
    op.add_column("desktop_builds", sa.Column("artifact_sha256", sa.String(64), nullable=True))
    op.add_column("desktop_builds", sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column(
        "desktop_builds",
        sa.Column(
            "download_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now() + interval '72 hours'"),
        ),
    )
    op.add_column(
        "desktop_builds",
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "desktop_builds",
        sa.Column("max_downloads", sa.Integer(), nullable=False, server_default="10"),
    )
    op.drop_column("desktop_builds", "consumed_at")
    op.alter_column("desktop_builds", "activation_token_hash", nullable=False)
    op.alter_column("desktop_builds", "activation_token_expires_at", nullable=False)
