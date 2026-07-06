"""
RBAC permission constants and plan-based feature limits.

Usage:
    from app.core.permissions import PlanLimits, can_access_feature

    limits = PlanLimits.for_plan(org.plan)
    if limits.max_members and member_count >= limits.max_members:
        raise PaymentRequiredError("Upgrade to invite more members.")
"""

from app.config import project
from app.core.exceptions import PaymentRequiredError
from app.models.organization import PlanTier


class PlanLimits:
    max_members: int | None
    max_projects: int | None
    audit_log_retention_days: int
    mfa_required: bool
    sso_enabled: bool
    priority_support: bool

    def __init__(self, plan: PlanTier) -> None:
        entry = getattr(project.plan_limits, plan.name)
        self.max_members = entry.max_members
        self.max_projects = entry.max_projects
        self.audit_log_retention_days = entry.audit_log_retention_days
        self.mfa_required = entry.mfa_required
        self.sso_enabled = entry.sso_enabled
        self.priority_support = entry.priority_support

    @classmethod
    def for_plan(cls, plan: PlanTier) -> "PlanLimits":
        return cls(plan)


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
        "mfa": limits.mfa_required,
        "priority_support": limits.priority_support,
    }
    if feature in feature_map and not feature_map[feature]:
        raise PaymentRequiredError(
            f"The '{feature}' feature is not available on your current plan. "
            "Please upgrade to access it."
        )
