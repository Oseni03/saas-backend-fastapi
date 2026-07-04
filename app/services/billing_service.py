"""
Billing service — Paystack integration.

Paystack flow:
  1. initialize_transaction() → returns authorization_url, redirect user there
  2. User pays → Paystack redirects to callback_url?reference=xxx
  3. verify_transaction(reference) → confirms payment, syncs plan to DB
  4. Webhooks at /webhooks/paystack → charge.success, subscription.create,
     subscription.disable, invoice.payment_failed
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from dateutil.relativedelta import relativedelta

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import project, settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.lib.logger import logger
from app.lib.ulid import new_ulid
from app.models.organization import Organization, PlanTier
from app.models.subscription import Subscription, SubscriptionStatus
from app.repositories.org_repo import OrganizationRepository

PLAN_CODE_MAP: dict[PlanTier, str] = {
    PlanTier.PRO: settings.PAYSTACK_PRO_PLAN_CODE,
    PlanTier.ENTERPRISE: settings.PAYSTACK_ENTERPRISE_PLAN_CODE,
}

CODE_PLAN_MAP: dict[str, PlanTier] = {
    v: k for k, v in PLAN_CODE_MAP.items() if v
}


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.org_repo = OrganizationRepository(db)

    # ── Initialize ────────────────────────────────────────────────────

    async def initialize_transaction(
        self,
        org: Organization,
        plan: PlanTier,
        user_email: str,
        callback_url: str,
    ) -> str:
        """Returns the Paystack authorization_url — redirect the user there."""
        if plan == PlanTier.FREE:
            raise BadRequestError("Cannot create checkout for the free plan.")

        plan_code = PLAN_CODE_MAP.get(plan)
        if not plan_code:
            raise BadRequestError(f"No Paystack plan configured for plan: {plan}")

        reference = f"{org.id}_{plan.value}_{int(datetime.now(UTC).timestamp())}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{project.billing.paystack_api_base_url}/transaction/initialize",
                headers=_headers(),
                json={
                    "email": user_email,
                    "amount": 0,
                    "plan": plan_code,
                    "callback_url": callback_url,
                    "reference": reference,
                    "metadata": {
                        "organization_id": org.id,
                        "plan": plan.value,
                        "cancel_action": callback_url + "?status=cancelled",
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

        logger.info("billing.transaction_initialized", org_id=org.id, plan=plan, reference=reference)
        return data["data"]["authorization_url"]

    # ── Verify ────────────────────────────────────────────────────────

    async def verify_transaction(self, reference: str) -> dict:  # type: ignore[type-arg]
        """
        Verify a completed payment and sync the plan + subscription to the DB.
        Call after Paystack redirects with ?reference=xxx.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{project.billing.paystack_api_base_url}/transaction/verify/{reference}",
                headers=_headers(),
            )
            resp.raise_for_status()
            tx = resp.json()["data"]

        if tx["status"] != "success":
            raise BadRequestError(
                f"Transaction '{reference}' was not successful (status: {tx['status']})"
            )

        org_id: str = (tx.get("metadata") or {}).get("organization_id", "")
        if not org_id:
            raise BadRequestError("Transaction metadata missing organization_id.")

        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organization")

        plan = CODE_PLAN_MAP.get(tx.get("plan", {}).get("plan_code", ""), PlanTier.FREE)

        # Persist customer code
        org.paystack_customer_id = tx["customer"]["customer_code"]
        org.plan = plan
        await self.org_repo.save(org)

        # Upsert subscription if one was created
        sub_data = tx.get("subscription") or {}
        if sub_data.get("subscription_code"):
            await self._upsert_subscription_record(
                org_id=org_id,
                sub_code=sub_data["subscription_code"],
                plan_code=tx.get("plan", {}).get("plan_code", ""),
                status=SubscriptionStatus.ACTIVE,
            )

        logger.info("billing.transaction_verified", org_id=org_id, plan=plan, reference=reference)
        return {"org_id": org_id, "plan": plan}

    # ── Cancel ────────────────────────────────────────────────────────

    async def cancel_subscription(self, org: Organization) -> None:
        """Disable the active subscription via Paystack API."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.organization_id == org.id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise NotFoundError("Subscription")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{project.billing.paystack_api_base_url}/subscription/disable",
                headers=_headers(),
                json={"code": sub.paystack_sub_code, "token": sub.paystack_plan_code},
            )
            resp.raise_for_status()

        sub.status = SubscriptionStatus.CANCELED
        sub.canceled_at = datetime.now(UTC)
        org.plan = PlanTier.FREE
        await self.org_repo.save(org)
        logger.info("billing.subscription_canceled", org_id=org.id)

    # ── Manage URL ────────────────────────────────────────────────────

    async def get_manage_url(self, org: Organization) -> str:
        """
        Paystack has no hosted portal — return a URL to your own billing page
        pre-scoped to the customer code.
        """
        if not org.paystack_customer_id:
            raise BadRequestError("No billing account found. Subscribe to a plan first.")
        return f"{settings.FRONTEND_URL}/billing/manage?customer={org.paystack_customer_id}"

    # ── Webhooks ──────────────────────────────────────────────────────

    async def handle_webhook(self, payload: bytes, signature: str) -> None:
        """
        Verify Paystack HMAC-SHA512 signature, then dispatch to event handlers.
        Paystack sends X-Paystack-Signature header.
        """
        hash_func = getattr(hashlib, project.billing.webhook_hmac_algorithm)
        expected = hmac.new(
            settings.PAYSTACK_WEBHOOK_SECRET.encode(),
            payload,
            hash_func,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise BadRequestError("Invalid webhook signature.")

        event: dict = json.loads(payload)  # type: ignore[type-arg]
        event_type: str = event.get("event", "")
        data: dict = event.get("data", {})  # type: ignore[type-arg]

        handlers = {
            "charge.success":         self._on_charge_success,
            "subscription.create":    self._on_subscription_create,
            "subscription.disable":   self._on_subscription_disable,
            "invoice.payment_failed": self._on_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(data)
            logger.info("billing.webhook_handled", event_type=event_type)
        else:
            logger.debug("billing.webhook_ignored", event_type=event_type)

    # ── Webhook event handlers ────────────────────────────────────────

    async def _on_charge_success(self, data: dict) -> None:  # type: ignore[type-arg]
        metadata = data.get("metadata") or {}
        org_id = metadata.get("organization_id")
        plan_key = metadata.get("plan", "")
        if not org_id:
            return

        try:
            plan = PlanTier(plan_key)
        except ValueError:
            plan = PlanTier.FREE

        org = await self.org_repo.get_by_id(org_id)
        if org:
            org.plan = plan
            await self.org_repo.save(org)
        logger.info("billing.charge_success", org_id=org_id, plan=plan)

    async def _on_subscription_create(self, data: dict) -> None:  # type: ignore[type-arg]
        metadata = (data.get("metadata") or {})
        org_id = metadata.get("organization_id")
        if not org_id:
            return

        plan = CODE_PLAN_MAP.get(
            (data.get("plan") or {}).get("plan_code", ""), PlanTier.FREE
        )
        sub_code = data.get("subscription_code", "")
        plan_code = (data.get("plan") or {}).get("plan_code", "")

        await self._upsert_subscription_record(
            org_id=org_id,
            sub_code=sub_code,
            plan_code=plan_code,
            status=SubscriptionStatus.ACTIVE,
            next_payment=data.get("next_payment_date"),
        )

        org = await self.org_repo.get_by_id(org_id)
        if org:
            org.plan = plan
            await self.org_repo.save(org)

    async def _on_subscription_disable(self, data: dict) -> None:  # type: ignore[type-arg]
        sub_code = data.get("subscription_code", "")
        metadata = (data.get("metadata") or {})
        org_id = metadata.get("organization_id")

        result = await self.db.execute(
            select(Subscription).where(Subscription.paystack_sub_code == sub_code)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = datetime.now(UTC)

        if org_id:
            org = await self.org_repo.get_by_id(org_id)
            if org:
                org.plan = PlanTier.FREE
                await self.org_repo.save(org)

        logger.info("billing.subscription_disabled", org_id=org_id, sub_code=sub_code)

    async def _on_payment_failed(self, data: dict) -> None:  # type: ignore[type-arg]
        sub_code = (data.get("subscription") or {}).get("subscription_code", "")
        result = await self.db.execute(
            select(Subscription).where(Subscription.paystack_sub_code == sub_code)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            await self.db.flush()

        logger.warning("billing.payment_failed", sub_code=sub_code)

    # ── Internal ──────────────────────────────────────────────────────

    async def _upsert_subscription_record(
        self,
        org_id: str,
        sub_code: str,
        plan_code: str,
        status: SubscriptionStatus,
        next_payment: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        period_end = (
            datetime.fromisoformat(next_payment.replace("Z", "+00:00"))
            if next_payment
            else now + relativedelta(months=project.billing.next_billing_month_offset)
        )

        result = await self.db.execute(
            select(Subscription).where(Subscription.organization_id == org_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.paystack_sub_code = sub_code
            existing.paystack_plan_code = plan_code
            existing.status = status
            existing.current_period_start = now
            existing.current_period_end = period_end
        else:
            self.db.add(Subscription(
                id=new_ulid(),
                organization_id=org_id,
                paystack_sub_code=sub_code,
                paystack_plan_code=plan_code,
                status=status,
                current_period_start=now,
                current_period_end=period_end,
            ))

        await self.db.flush()
