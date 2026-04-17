"""add follow source fields to account_settings

Revision ID: b1c3e5f7a9d2
Revises: a6f724212d1a
Create Date: 2026-04-16 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c3e5f7a9d2"
down_revision: Union[str, None] = "a6f724212d1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("account_settings", sa.Column("list_tab", sa.String(150), nullable=True))
    op.add_column("account_settings", sa.Column("account_group", sa.String(500), nullable=True))
    op.add_column("account_settings", sa.Column("account_list_tab", sa.String(150), nullable=True))


def downgrade() -> None:
    op.drop_column("account_settings", "account_list_tab")
    op.drop_column("account_settings", "account_group")
    op.drop_column("account_settings", "list_tab")
