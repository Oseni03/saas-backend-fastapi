from app.models.membership import MemberRole, Membership
from app.services.membership_policy import MembershipPolicy


def test_membership_policy_allows_admin_and_owner() -> None:
    admin_membership = Membership(role=MemberRole.ADMIN)
    owner_membership = Membership(role=MemberRole.OWNER)

    MembershipPolicy.ensure_role(admin_membership, MemberRole.MEMBER)
    MembershipPolicy.ensure_role(owner_membership, MemberRole.ADMIN)


def test_membership_policy_rejects_viewer() -> None:
    viewer_membership = Membership(role=MemberRole.VIEWER)

    try:
        MembershipPolicy.ensure_role(viewer_membership, MemberRole.MEMBER)
    except Exception as exc:
        assert exc.__class__.__name__ == "ForbiddenError"
    else:
        raise AssertionError("Viewer should not satisfy MEMBER permission")
