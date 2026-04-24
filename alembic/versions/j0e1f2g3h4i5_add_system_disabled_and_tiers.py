"""Add system_disabled to accounts and update plan tiers.

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa

revision = "j0e1f2g3h4i5"
down_revision = "i9d0e1f2g3h4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add system_disabled column to accounts
    op.add_column(
        "accounts",
        sa.Column("system_disabled", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Migrate existing 'pro' tier to 'walk'
    op.execute("UPDATE users SET plan_tier = 'walk' WHERE plan_tier = 'pro'")
    op.execute("UPDATE subscriptions SET plan_tier = 'walk' WHERE plan_tier = 'pro'")

    # Set ahmartin@gmail.com to walk tier, active
    op.execute("""
        UPDATE subscriptions SET status = 'active', plan_tier = 'walk'
        WHERE user_id = (SELECT id FROM users WHERE email = 'ahmartin@gmail.com')
    """)
    op.execute("UPDATE users SET plan_tier = 'walk' WHERE email = 'ahmartin@gmail.com'")


def downgrade() -> None:
    op.execute("UPDATE users SET plan_tier = 'pro' WHERE plan_tier IN ('crawl', 'walk', 'run')")
    op.execute("UPDATE subscriptions SET plan_tier = 'pro' WHERE plan_tier IN ('crawl', 'walk', 'run')")
    op.drop_column("accounts", "system_disabled")
