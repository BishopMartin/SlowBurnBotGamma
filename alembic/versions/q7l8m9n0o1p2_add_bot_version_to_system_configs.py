"""Add current_bot_version and current_bot_release_date to system_configs.

Revision ID: q7l8m9n0o1p2
Revises: p6k7l8m9n0o1
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = "q7l8m9n0o1p2"
down_revision = "p6k7l8m9n0o1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("system_configs", sa.Column("current_bot_version", sa.String(50), nullable=True))
    op.add_column("system_configs", sa.Column("current_bot_release_date", sa.String(50), nullable=True))
    # Seed current version on the existing singleton row if present
    op.execute(
        "UPDATE system_configs SET current_bot_version = '1.035', current_bot_release_date = 'Apr 30 2026' "
        "WHERE current_bot_version IS NULL"
    )


def downgrade() -> None:
    op.drop_column("system_configs", "current_bot_release_date")
    op.drop_column("system_configs", "current_bot_version")
