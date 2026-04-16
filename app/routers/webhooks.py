"""Stripe webhook handler with signature verification and idempotency."""
import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.subscription import Subscription
from app.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Events we handle — all others are silently ignored
HANDLED_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
}


async def _upsert_subscription(session: AsyncSession, stripe_sub) -> None:
    """Update our subscriptions table from a Stripe subscription object."""
    from datetime import datetime, timezone

    result = await session.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub.id
        )
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        # Try to find by customer id
        result = await session.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == stripe_sub.customer
            )
        )
        sub = result.scalar_one_or_none()

    if sub is None:
        logger.warning("Stripe webhook: no subscription found for %s", stripe_sub.id)
        return

    sub.stripe_subscription_id = stripe_sub.id
    sub.stripe_customer_id = stripe_sub.customer
    sub.status = stripe_sub.status
    sub.current_period_start = datetime.fromtimestamp(
        stripe_sub.current_period_start, tz=timezone.utc
    )
    sub.current_period_end = datetime.fromtimestamp(
        stripe_sub.current_period_end, tz=timezone.utc
    )
    await session.commit()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    session: AsyncSession = Depends(get_async_session),
):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook not configured.")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature.")

    event_type = event["type"]

    if event_type not in HANDLED_EVENTS:
        return {"received": True}

    logger.info("Stripe event: %s id=%s", event_type, event["id"])

    try:
        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            await _upsert_subscription(session, event["data"]["object"])

        elif event_type == "invoice.payment_failed":
            stripe_sub_id = event["data"]["object"].get("subscription")
            if stripe_sub_id:
                result = await session.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == stripe_sub_id
                    )
                )
                sub = result.scalar_one_or_none()
                if sub:
                    sub.status = "past_due"
                    await session.commit()

    except Exception:
        logger.exception("Error processing Stripe event %s", event["id"])
        raise HTTPException(status_code=500, detail="Webhook processing error.")

    return {"received": True}
