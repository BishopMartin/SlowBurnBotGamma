"""Stripe webhook handler with signature verification and idempotency."""
import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.processed_stripe_event import ProcessedStripeEvent
from app.models.subscription import Subscription
from app.services.stripe_sync import apply_stripe_subscription
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
    event_id = event["id"]

    if event_type not in HANDLED_EVENTS:
        return {"received": True}

    # Claim the event id for idempotency.  Flush only — if the row is a
    # duplicate the PK conflict raises immediately and we short-circuit.
    # Otherwise the claim is pending in this transaction; processing below
    # commits both the claim and any DB updates atomically, so a transient
    # failure rolls back the claim and Stripe's retry can land cleanly.
    session.add(ProcessedStripeEvent(event_id=event_id))
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        logger.info("Stripe event %s already processed; skipping.", event_id)
        return {"received": True, "duplicate": True}

    logger.info("Stripe event: %s id=%s", event_type, event_id)

    try:
        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            await apply_stripe_subscription(session, event["data"]["object"])

        elif event_type == "invoice.payment_succeeded":
            stripe_sub_id = event["data"]["object"].get("subscription")
            if stripe_sub_id and settings.stripe_secret_key:
                stripe.api_key = settings.stripe_secret_key
                stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
                await apply_stripe_subscription(session, stripe_sub)

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

    except IntegrityError:
        # Concurrent duplicate raced us at commit time; another worker won.
        await session.rollback()
        logger.info("Stripe event %s already processed; skipping.", event_id)
        return {"received": True, "duplicate": True}
    except Exception:
        await session.rollback()
        logger.exception("Error processing Stripe event %s", event_id)
        raise HTTPException(status_code=500, detail="Webhook processing error.")

    return {"received": True}
