"""add warning_message to session_logs

Revision ID: v2q3r4s5t6u7
Revises: u1p2q3r4s5t6
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa

revision = 'v2q3r4s5t6u7'
down_revision = 'u1p2q3r4s5t6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('session_logs', sa.Column('warning_message', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('session_logs', 'warning_message')
