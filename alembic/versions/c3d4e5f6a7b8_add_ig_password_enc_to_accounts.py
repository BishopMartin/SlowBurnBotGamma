"""add ig_password_enc to accounts

Revision ID: c3d4e5f6a7b8
Revises: b1c3e5f7a9d2
Create Date: 2026-04-19

"""
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b1c3e5f7a9d2"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("ig_password_enc", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "ig_password_enc")
