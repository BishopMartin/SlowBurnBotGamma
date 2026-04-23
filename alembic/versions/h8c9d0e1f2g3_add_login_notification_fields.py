"""add login notification fields to user_configs

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2026-04-23

"""
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2g3"
down_revision: Union[str, None] = "g7b8c9d0e1f2"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("user_configs", sa.Column("login_notices_type", sa.String(10), nullable=False, server_default=sa.text("'email'")))
    op.add_column("user_configs", sa.Column("login_notify_email", sa.String(255), nullable=True))
    op.add_column("user_configs", sa.Column("login_notify_phone", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("user_configs", "login_notify_phone")
    op.drop_column("user_configs", "login_notify_email")
    op.drop_column("user_configs", "login_notices_type")
