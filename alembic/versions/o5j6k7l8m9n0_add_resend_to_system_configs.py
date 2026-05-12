"""Add Resend API fields to system_configs.

Revision ID: o5j6k7l8m9n0
Revises: n4i5j6k7l8m9
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa


revision = "o5j6k7l8m9n0"
down_revision = "n4i5j6k7l8m9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("system_configs", sa.Column("resend_api_key_enc", sa.Text(), nullable=True))
    op.add_column("system_configs", sa.Column("resend_from_address", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("system_configs", "resend_from_address")
    op.drop_column("system_configs", "resend_api_key_enc")
