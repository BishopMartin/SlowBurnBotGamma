"""add system_configs table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-20

"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "system_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("smtp_server", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default=sa.text("587")),
        sa.Column("smtp_user", sa.String(255), nullable=True),
        sa.Column("smtp_password_enc", sa.Text(), nullable=True),
        sa.Column("textbelt_key_enc", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_configs")
