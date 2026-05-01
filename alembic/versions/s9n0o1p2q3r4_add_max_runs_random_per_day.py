"""add max_runs_random_per_day to account_settings

Revision ID: s9n0o1p2q3r4
Revises: r8m9n0o1p2q3
Create Date: 2026-04-30

"""
from alembic import op
import sqlalchemy as sa


revision = "s9n0o1p2q3r4"
down_revision = "r8m9n0o1p2q3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "account_settings",
        sa.Column("max_runs_random_per_day", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("account_settings", "max_runs_random_per_day")
