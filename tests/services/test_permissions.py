"""Tests for plan-based permission enforcement."""

import pytest

from app.core.exceptions import PaymentRequiredError
from app.core.permissions import PlanLimits, assert_feature_available, assert_member_limit
from app.models.organization import PlanTier


def test_free_plan_limits() -> None:
    limits = PlanLimits.for_plan(PlanTier.FREE)
    assert limits.max_members == 5
    assert limits.sso_enabled is False
    assert limits.audit_log_retention_days == 7


def test_pro_plan_limits() -> None:
    limits = PlanLimits.for_plan(PlanTier.PRO)
    assert limits.max_members == 50
    assert limits.priority_support is True


def test_enterprise_plan_limits() -> None:
    limits = PlanLimits.for_plan(PlanTier.ENTERPRISE)
    assert limits.max_members is None  # Unlimited
    assert limits.sso_enabled is True
    assert limits.mfa_required is True


def test_member_limit_enforced_on_free() -> None:
    with pytest.raises(PaymentRequiredError):
        assert_member_limit(PlanTier.FREE, current_count=5)  # At limit


def test_member_limit_not_exceeded() -> None:
    assert_member_limit(PlanTier.FREE, current_count=4)  # OK


def test_member_limit_unlimited_on_enterprise() -> None:
    assert_member_limit(PlanTier.ENTERPRISE, current_count=9999)  # No limit


def test_sso_blocked_on_free() -> None:
    with pytest.raises(PaymentRequiredError):
        assert_feature_available(PlanTier.FREE, "sso")


def test_sso_allowed_on_enterprise() -> None:
    assert_feature_available(PlanTier.ENTERPRISE, "sso")  # No exception
