"""Add last_session_account to client_heartbeats.

Revision ID: r8m9n0o1p2q3
Revises: q7l8m9n0o1p2
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = "r8m9n0o1p2q3"
down_revision = "q7l8m9n0o1p2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE client_heartbeats ADD COLUMN IF NOT EXISTS last_session_account TEXT")


def downgrade() -> None:
    op.drop_column("client_heartbeats", "last_session_account")
