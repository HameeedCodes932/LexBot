import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import User, Invoice, FeatureUsage, Analytics

logger = logging.getLogger(__name__)

stripe = None
if config.BILLING_ENABLED:
    import stripe as _stripe
    stripe = _stripe
    stripe.api_key = config.STRIPE_SECRET_KEY


# ── Helpers ────────────────────────────────────────────────────────────────────

def _plan_for_price(price_id: str) -> Optional[str]:
    for plan_id, plan in config.PLANS.items():
        if plan["stripe_price_id"] == price_id:
            return plan_id
    return "free"


def _get_plan(plan_id: str) -> dict:
    return config.PLANS.get(plan_id, config.PLANS["free"])


async def get_user_plan(session: AsyncSession, user_id: int) -> dict:
    user_stmt = select(User.org_id, User.subscription_status, User.stripe_price_id).where(User.id == user_id)
    res = await session.execute(user_stmt)
    row = res.one_or_none()
    if not row:
        return {**config.PLANS["free"], "plan_id": "free", "status": "free"}
    
    org_id, status, price_id = row
    
    if org_id:
        from database import Organization
        org_stmt = select(Organization.owner_id, Organization.subscription_status).where(Organization.id == org_id)
        org_res = await session.execute(org_stmt)
        org_row = org_res.one_or_none()
        if org_row:
            owner_id, status = org_row
            # Inherit owner's plan details
            owner_price_stmt = select(User.stripe_price_id).where(User.id == owner_id)
            price_id = await session.scalar(owner_price_stmt)

    if status in ("active", "trialing"):
        plan_id = _plan_for_price(price_id) if price_id else "free"
    else:
        plan_id = "free"
        
    return {**config.PLANS.get(plan_id, config.PLANS["free"]), "plan_id": plan_id, "status": status or "free"}


# ── Usage metering ─────────────────────────────────────────────────────────────

async def get_monthly_usage(session: AsyncSession, user_id: int) -> dict:
    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Check if user is in an org
    user_stmt = select(User.org_id).where(User.id == user_id)
    org_id = await session.scalar(user_stmt)

    if org_id:
        # Sum usage across all members of the organization
        member_stmt = select(User.id).where(User.org_id == org_id)
        res = await session.execute(member_stmt)
        user_ids = list(res.scalars().all())
    else:
        user_ids = [user_id]

    if not user_ids:
        user_ids = [user_id]

    # Chat queries
    query_count = await session.scalar(
        select(func.count(Analytics.id)).where(
            Analytics.user_id.in_(user_ids),
            Analytics.created_at >= first_of_month,
        )
    )

    # Actually count documents:
    from database import Document
    doc_count_val = await session.scalar(
        select(func.count(Document.id)).where(Document.user_id.in_(user_ids))
    )

    # Feature usage counts
    feature_counts = {}
    for feat in ("extract-clauses", "compare-clauses"):
        count = await session.scalar(
            select(func.count(FeatureUsage.id)).where(
                FeatureUsage.user_id.in_(user_ids),
                FeatureUsage.feature_name == feat,
                FeatureUsage.created_at >= first_of_month,
            )
        )
        feature_counts[feat] = count or 0

    return {
        "queries_used": query_count or 0,
        "documents_used": doc_count_val or 0,
        "feature_usage": feature_counts,
        "period_start": first_of_month.isoformat(),
        "period_end": now.isoformat(),
    }


async def check_feature_access(
    session: AsyncSession, user_id: int, feature: str
) -> dict:
    plan = await get_user_plan(session, user_id)
    usage = await get_monthly_usage(session, user_id)

    if feature not in plan.get("features", []):
        return {"allowed": False, "reason": "upgrade_plan", "plan": plan, "usage": usage}

    if usage["queries_used"] >= plan["max_queries_monthly"]:
        return {"allowed": False, "reason": "query_limit", "plan": plan, "usage": usage}

    if feature == "documents" and usage["documents_used"] >= plan["max_documents"]:
        return {"allowed": False, "reason": "doc_limit", "plan": plan, "usage": usage}

    return {"allowed": True, "reason": None, "plan": plan, "usage": usage}


# ── Stripe operations (demo mode safe) ─────────────────────────────────────────

async def create_checkout_session(user_id: int, price_id: str, origin: str) -> str:
    if not config.BILLING_ENABLED or stripe is None:
        logger.info("Demo mode: would create checkout for user=%d price=%s", user_id, price_id)
        return f"{origin}/billing?demo=upgrade&price={price_id}"

    from fastapi import HTTPException
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            client_reference_id=str(user_id),
            success_url=f"{origin}/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/billing?canceled=true",
            subscription_data={"trial_period_days": config.STRIPE_TRIAL_DAYS},
        )
        return session.url
    except Exception as e:
        logger.error("Stripe checkout failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment service unavailable.")


async def create_portal_session(user_id: int, stripe_customer_id: str, origin: str) -> str:
    if not config.BILLING_ENABLED or stripe is None:
        logger.info("Demo mode: would create portal session for user=%d", user_id)
        return f"{origin}/billing"

    from fastapi import HTTPException
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{origin}/billing",
        )
        return session.url
    except Exception as e:
        logger.error("Stripe portal failed: %s", e)
        raise HTTPException(status_code=502, detail="Billing portal unavailable.")


async def get_or_create_customer(session: AsyncSession, user: dict) -> str:
    if user.get("stripe_customer_id"):
        return user["stripe_customer_id"]

    if not config.BILLING_ENABLED or stripe is None:
        return "cus_demo"

    try:
        customer = stripe.Customer.create(
            email=user["email"],
            name=user.get("username", ""),
            metadata={"user_id": str(user["id"])},
        )
        await session.execute(
            update(User)
            .where(User.id == user["id"])
            .values(stripe_customer_id=customer.id)
        )
        return customer.id
    except Exception as e:
        logger.error("Stripe customer creation failed: %s", e)
        return "cus_demo"


# ── Webhook handler ────────────────────────────────────────────────────────────

async def handle_webhook(payload: bytes, sig_header: str) -> dict:
    if not config.BILLING_ENABLED or stripe is None:
        return {"status": "demo_mode"}

    from fastapi import HTTPException
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, config.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    logger.info("Stripe webhook: %s %s", event_type, data.get("id", ""))

    async with __import__("database", fromlist=["get_session"]).async_session_factory() as db:
        try:
            if event_type in ("checkout.session.completed", "invoice.paid"):
                await _handle_checkout_completed(db, data)
            elif event_type == "customer.subscription.updated":
                await _handle_subscription_updated(db, data)
            elif event_type == "customer.subscription.deleted":
                await _handle_subscription_deleted(db, data)
            elif event_type == "invoice.payment_failed":
                await _handle_invoice_payment_failed(db, data)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("Webhook handler error: %s", e)

    return {"status": "ok"}


async def _handle_checkout_completed(session: AsyncSession, data: dict):
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    client_ref = data.get("client_reference_id")
    if not client_ref:
        return
    user_id = int(client_ref)

    sub_data = {}
    if subscription_id:
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            items = sub.get("items", {}).get("data", [])
            price_id = items[0]["price"]["id"] if items else None
            current_period_end = datetime.fromtimestamp(sub.get("current_period_end", 0))
            status = sub.get("status", "active")
            sub_data = {
                "stripe_subscription_id": subscription_id,
                "stripe_price_id": price_id,
                "subscription_status": status,
                "current_period_end": current_period_end,
            }
        except Exception as e:
            logger.warning("Could not retrieve subscription %s: %s", subscription_id, e)
            sub_data["subscription_status"] = "active"

    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(stripe_customer_id=customer_id, **sub_data)
    )
    logger.info("User %d subscribed (checkout completed)", user_id)


async def _handle_subscription_updated(session: AsyncSession, data: dict):
    customer_id = data.get("customer")
    sub_id = data.get("id")
    status = data.get("status", "active")
    items = data.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else None
    current_period_end = datetime.fromtimestamp(data.get("current_period_end", 0))

    result = await session.execute(
        select(User.id).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("No user for customer %s", customer_id)
        return

    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            stripe_subscription_id=sub_id,
            stripe_price_id=price_id,
            subscription_status=status,
            current_period_end=current_period_end,
        )
    )
    logger.info("Subscription updated for user %d: %s", user.id, status)


async def _handle_subscription_deleted(session: AsyncSession, data: dict):
    customer_id = data.get("customer")
    result = await session.execute(
        select(User.id).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return
    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            subscription_status="canceled",
            stripe_subscription_id=None,
            stripe_price_id=None,
            current_period_end=None,
        )
    )
    logger.info("Subscription canceled for user %d", user.id)


async def _handle_invoice_payment_failed(session: AsyncSession, data: dict):
    customer_id = data.get("customer")
    invoice_id = data.get("id")
    pdf = data.get("invoice_pdf", "")

    result = await session.execute(
        select(User.id).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(subscription_status="past_due")
    )

    invoice = Invoice(
        user_id=user.id,
        stripe_invoice_id=invoice_id,
        status="failed",
        invoice_pdf=pdf,
    )
    session.add(invoice)
    logger.warning("Payment failed for user %d invoice %s", user.id, invoice_id)
