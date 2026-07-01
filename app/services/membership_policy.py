from app.core.exceptions import ForbiddenError
from app.models.membership import MemberRole, Membership


class MembershipPolicy:
    """Deepened seam for Organization membership and permission rules."""

    role_rank = {
        MemberRole.VIEWER: 0,
        MemberRole.MEMBER: 1,
        MemberRole.ADMIN: 2,
        MemberRole.OWNER: 3,
    }

    @classmethod
    def ensure_role(cls, membership: Membership, minimum: MemberRole) -> None:
        if cls.role_rank[membership.role] < cls.role_rank[minimum]:
            raise ForbiddenError("You do not have sufficient permissions.")

    @classmethod
    def can_manage_members(cls, membership: Membership) -> bool:
        return cls.role_rank[membership.role] >= cls.role_rank[MemberRole.ADMIN]
