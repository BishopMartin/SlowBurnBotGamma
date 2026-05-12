"""Add resend_reply_to to system_configs.

Revision ID: p6k7l8m9n0o1
Revises: o5j6k7l8m9n0
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa


revision = "p6k7l8m9n0o1"
down_revision = "o5j6k7l8m9n0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("system_configs", sa.Column("resend_reply_to", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("system_configs", "resend_reply_to")
