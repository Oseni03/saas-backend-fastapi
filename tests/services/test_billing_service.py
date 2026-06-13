"""
Tests for the billing service — Paystack interactions are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import BadRequestError
from app.models.organization import Organization, PlanTier
from app.services.billing_service import BillingService


def _make_org(db_session, plan: PlanTier = PlanTier.FREE) -> Organization:
    from app.lib.ulid import new_ulid
    org = Organization(id=new_ulid(), name="Test Org", slug="test-org", plan=plan)
    db_session.add(org)
    return org


@pytest.mark.asyncio
async def test_initialize_free_plan_raises(db_session) -> None:
    org = _make_org(db_session)
    await db_session.flush()

    svc = BillingService(db_session)
    with pytest.raises(BadRequestError, match="free plan"):
        await svc.initialize_transaction(
            org=org,
            plan=PlanTier.FREE,
            user_email="owner@example.com",
            callback_url="http://localhost:3000/billing/callback",
        )


@pytest.mark.asyncio
async def test_initialize_missing_plan_code_raises(db_session) -> None:
    org = _make_org(db_session)
    await db_session.flush()

    # Ensure plan codes are empty so we get a config error
    with patch("app.services.billing_service.PLAN_CODE_MAP", {PlanTier.PRO: ""}):
        svc = BillingService(db_session)
        with pytest.raises(BadRequestError, match="No Paystack plan configured"):
            await svc.initialize_transaction(
                org=org,
                plan=PlanTier.PRO,
                user_email="owner@example.com",
                callback_url="http://localhost:3000/billing/callback",
            )


@pytest.mark.asyncio
async def test_initialize_returns_authorization_url(db_session) -> None:
    org = _make_org(db_session)
    await db_session.flush()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "authorization_url": "https://checkout.paystack.com/test123",
            "access_code": "test_code",
            "reference": "ref_test",
        }
    }
    mock_response.raise_for_status = MagicMock()

    with (
        patch("app.services.billing_service.PLAN_CODE_MAP", {PlanTier.PRO: "PLN_test"}),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        svc = BillingService(db_session)
        url = await svc.initialize_transaction(
            org=org,
            plan=PlanTier.PRO,
            user_email="owner@example.com",
            callback_url="http://localhost:3000/billing/callback",
        )

    assert url == "https://checkout.paystack.com/test123"


@pytest.mark.asyncio
async def test_get_manage_url_no_customer_raises(db_session) -> None:
    org = _make_org(db_session)
    await db_session.flush()
    assert org.paystack_customer_id is None

    svc = BillingService(db_session)
    with pytest.raises(BadRequestError, match="No billing account"):
        await svc.get_manage_url(org)


@pytest.mark.asyncio
async def test_get_manage_url_returns_url(db_session) -> None:
    org = _make_org(db_session)
    org.paystack_customer_id = "CUS_test123"
    await db_session.flush()

    svc = BillingService(db_session)
    url = await svc.get_manage_url(org)
    assert "CUS_test123" in url


@pytest.mark.asyncio
async def test_cancel_subscription_no_sub_raises(db_session) -> None:
    org = _make_org(db_session)
    await db_session.flush()

    svc = BillingService(db_session)
    from app.core.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        await svc.cancel_subscription(org)


@pytest.mark.asyncio
async def test_handle_webhook_invalid_signature_raises(db_session) -> None:
    svc = BillingService(db_session)
    payload = b'{"event": "charge.success", "data": {}}'
    with pytest.raises(BadRequestError, match="signature"):
        await svc.handle_webhook(payload, "invalid-signature")


@pytest.mark.asyncio
async def test_handle_webhook_valid_signature(db_session) -> None:
    import hashlib
    import hmac
    from app.config import settings

    svc = BillingService(db_session)
    payload = b'{"event": "charge.success", "data": {"metadata": {}}}'
    sig = hmac.new(
        settings.PAYSTACK_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha512,
    ).hexdigest()

    # Should not raise — unknown org_id is handled gracefully
    await svc.handle_webhook(payload, sig)
