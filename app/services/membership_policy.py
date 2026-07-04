from app.config import project
from app.core.exceptions import ForbiddenError
from app.models.membership import MemberRole, Membership


class MembershipPolicy:
    """Deepened seam for Organization membership and permission rules."""

    @classmethod
    def _rank(cls, role: MemberRole) -> int:
        return project.role_rank[role.name]

    @classmethod
    def ensure_role(cls, membership: Membership, minimum: MemberRole) -> None:
        if cls._rank(membership.role) < cls._rank(minimum):
            raise ForbiddenError("You do not have sufficient permissions.")

    @classmethod
    def can_manage_members(cls, membership: Membership) -> bool:
        return cls._rank(membership.role) >= cls._rank(MemberRole.ADMIN)
