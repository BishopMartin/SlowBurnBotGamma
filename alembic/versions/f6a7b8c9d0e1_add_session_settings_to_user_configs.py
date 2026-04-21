"""add session settings to user_configs

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-21

"""
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("user_configs", sa.Column("like_suggested", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("user_configs", sa.Column("like_sponsored", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("user_configs", sa.Column("skip_login_check", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("user_configs", sa.Column("login_tries", sa.Integer(), nullable=False, server_default=sa.text("3")))


def downgrade() -> None:
    op.drop_column("user_configs", "login_tries")
    op.drop_column("user_configs", "skip_login_check")
    op.drop_column("user_configs", "like_sponsored")
    op.drop_column("user_configs", "like_suggested")
