"""Helpers for syncing Stripe Subscription objects into our DB.

Centralizes the int-timestamp → tz-aware datetime conversion and the
Stripe price-id → plan tier mapping so webhook and admin resync paths
stay consistent.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User
from app.plan_tiers import is_valid_tier
from app.services.plan_enforcement import enforce_account_limits
from app.settings import settings

logger = logging.getLogger(__name__)


def stripe_ts_to_datetime(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _price_to_tier_map() -> dict[str, str]:
    return {
        settings.stripe_price_crawl: "crawl",
        settings.stripe_price_walk: "walk",
        settings.stripe_price_run: "run",
    }


def _tier_from_stripe_sub(stripe_sub) -> str | None:
    mapping = _price_to_tier_map()
    items = getattr(stripe_sub, "items", None)
    data = getattr(items, "data", None) if items else None
    if not data:
        return None
    for item in data:
        price = getattr(item, "price", None)
        price_id = getattr(price, "id", None) if price else None
        if price_id and price_id in mapping and mapping[price_id]:
            return mapping[price_id]
    return None


async def apply_stripe_subscription(session: AsyncSession, stripe_sub) -> Subscription | None:
    """Upsert a Subscription row from a Stripe subscription object.

    Locates the row by stripe_subscription_id, then by stripe_customer_id.
    Updates status, period dates, and (when the price maps cleanly to a
    tier) both Subscription.plan_tier and User.plan_tier, then enforces
    account limits.  Caller is responsible for committing.
    """
    result = await session.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub.id
        )
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        result = await session.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == stripe_sub.customer
            )
        )
        sub = result.scalar_one_or_none()

    if sub is None:
        logger.warning("Stripe sync: no subscription row for %s", stripe_sub.id)
        return None

    sub.stripe_subscription_id = stripe_sub.id
    sub.stripe_customer_id = stripe_sub.customer
    sub.status = stripe_sub.status
    sub.current_period_start = stripe_ts_to_datetime(stripe_sub.current_period_start)
    sub.current_period_end = stripe_ts_to_datetime(stripe_sub.current_period_end)

    tier = _tier_from_stripe_sub(stripe_sub)
    if tier and is_valid_tier(tier):
        sub.plan_tier = tier
        user_result = await session.execute(select(User).where(User.id == sub.user_id))
        user = user_result.scalar_one_or_none()
        if user is not None:
            user.plan_tier = tier
        await enforce_account_limits(sub.user_id, session)

    return sub
