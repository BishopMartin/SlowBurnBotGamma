"""add bot_debug to user_configs

Revision ID: x4w9x0y1z2a3
Revises: w3v8w9x0y1z2
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

revision = 'x4w9x0y1z2a3'
down_revision = 'w3v8w9x0y1z2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'user_configs',
        sa.Column('bot_debug', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('user_configs', 'bot_debug')
