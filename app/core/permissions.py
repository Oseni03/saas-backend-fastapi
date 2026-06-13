"""
RBAC permission constants and plan-based feature limits.

Usage:
    from app.core.permissions import PlanLimits, can_access_feature

    limits = PlanLimits.for_plan(org.plan)
    if limits.max_members and member_count >= limits.max_members:
        raise PaymentRequiredError("Upgrade to invite more members.")
"""

from dataclasses import dataclass

from app.core.exceptions import PaymentRequiredError
from app.models.organization import PlanTier


@dataclass(frozen=True)
class PlanLimits:
    max_members: int | None       # None = unlimited
    max_projects: int | None
    audit_log_retention_days: int
    mfa_required: bool
    sso_enabled: bool
    priority_support: bool

    @classmethod
    def for_plan(cls, plan: PlanTier) -> "PlanLimits":
        return _PLAN_LIMITS[plan]


_PLAN_LIMITS: dict[PlanTier, PlanLimits] = {
    PlanTier.FREE: PlanLimits(
        max_members=5,
        max_projects=3,
        audit_log_retention_days=7,
        mfa_required=False,
        sso_enabled=False,
        priority_support=False,
    ),
    PlanTier.PRO: PlanLimits(
        max_members=50,
        max_projects=None,
        audit_log_retention_days=90,
        mfa_required=False,
        sso_enabled=False,
        priority_support=True,
    ),
    PlanTier.ENTERPRISE: PlanLimits(
        max_members=None,
        max_projects=None,
        audit_log_retention_days=365,
        mfa_required=True,
        sso_enabled=True,
        priority_support=True,
    ),
}


def assert_member_limit(plan: PlanTier, current_count: int) -> None:
    limits = PlanLimits.for_plan(plan)
    if limits.max_members is not None and current_count >= limits.max_members:
        raise PaymentRequiredError(
            f"Your plan allows a maximum of {limits.max_members} members. "
            "Upgrade to add more."
        )


def assert_feature_available(plan: PlanTier, feature: str) -> None:
    """
    feature: one of 'sso', 'audit_logs', 'priority_support'
    """
    limits = PlanLimits.for_plan(plan)
    feature_map = {
        "sso": limits.sso_enabled,
        "priority_support": limits.priority_support,
    }
    if feature in feature_map and not feature_map[feature]:
        raise PaymentRequiredError(
            f"The '{feature}' feature is not available on your current plan. "
            "Please upgrade to access it."
        )
