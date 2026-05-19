"""add vnc_pin to user_configs

Revision ID: u1p2q3r4s5t6
Revises: t0o1p2q3r4s5
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = 'u1p2q3r4s5t6'
down_revision = 't0o1p2q3r4s5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_configs', sa.Column('vnc_pin', sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column('user_configs', 'vnc_pin')
