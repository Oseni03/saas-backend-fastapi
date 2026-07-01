from fastapi import APIRouter, BackgroundTasks, status

from app.api.deps import CurrentUser, DBDep, VerifiedUser
from app.core.exceptions import NotFoundError
from app.lib.email import send_invitation_email
from app.models.membership import MemberRole
from app.repositories.org_repo import OrganizationRepository
from app.schemas.organization import (
    AcceptInvitationRequest,
    InviteMemberRequest,
    MembershipResponse,
    OrgCreateRequest,
    OrgResponse,
    OrgUpdateRequest,
    UpdateMemberRoleRequest,
    InvitationResponse,
)
from app.services.org_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    payload: OrgCreateRequest, current_user: VerifiedUser, db: DBDep
) -> OrgResponse:
    org = await OrganizationService(db).create(payload, current_user)
    return OrgResponse.model_validate(org)


@router.get("", response_model=list[OrgResponse])
async def list_orgs(current_user: CurrentUser, db: DBDep) -> list[OrgResponse]:
    orgs = await OrganizationService(db).list_for_user(current_user.id)
    return [OrgResponse.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(org_id: str, current_user: CurrentUser, db: DBDep) -> OrgResponse:
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    return OrgResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrgResponse)
async def update_org(
    org_id: str, payload: OrgUpdateRequest, current_user: CurrentUser, db: DBDep
) -> OrgResponse:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    updated = await svc.update(org, payload, current_user)
    return OrgResponse.model_validate(updated)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(org_id: str, current_user: CurrentUser, db: DBDep) -> None:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    await svc.delete(org, current_user)


# ── Members ───────────────────────────────────────────────────────────

@router.get("/{org_id}/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    org_id: str, current_user: CurrentUser, db: DBDep
) -> list[InvitationResponse]:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    invitations = await svc.list_invitations(org, current_user)
    return [InvitationResponse.model_validate(i) for i in invitations]

@router.post("/{org_id}/invitations", status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: str,
    payload: InviteMemberRequest,
    current_user: CurrentUser,
    db: DBDep,
    background_tasks: BackgroundTasks,
) -> dict:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    invitation, raw_token = await svc.invite_member(org, payload.email, payload.role, current_user)
    background_tasks.add_task(
        send_invitation_email,
        to=payload.email,
        invited_by=current_user.full_name or current_user.email,
        org_name=org.name,
        token=raw_token,
        role=payload.role.value,
    )
    return {"message": "Invitation sent."}


@router.delete("/{org_id}/invitations/{invitation_id}")
async def revoke_invitation(
    org_id: str, invitation_id: str, current_user: CurrentUser, db: DBDep
) -> dict:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    await svc.revoke_invitation(org, invitation_id, current_user)
    return {"message": "Invitation revoked."}


@router.post("/invitations/accept", response_model=OrgResponse)
async def accept_invitation(
    payload: AcceptInvitationRequest, current_user: CurrentUser, db: DBDep
) -> OrgResponse:
    org = await OrganizationService(db).accept_invitation(payload.token, current_user)
    return OrgResponse.model_validate(org)


@router.get("/{org_id}/members", response_model=list[MembershipResponse])
async def list_members(org_id: str, current_user: CurrentUser, db: DBDep) -> list[MembershipResponse]:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    members = await svc.list_members(org, current_user)
    return [
        MembershipResponse(
            user_id=m.user_id,
            organization_id=m.organization_id,
            role=m.role,
            created_at=m.created_at,
            name=u.full_name,
            email=u.email,
            avatar_url=u.avatar_url,
        )
        for m, u in members
    ]


@router.patch("/{org_id}/members/{user_id}", response_model=MembershipResponse)
async def update_member_role(
    org_id: str,
    user_id: str,
    payload: UpdateMemberRoleRequest,
    current_user: CurrentUser,
    db: DBDep,
) -> MembershipResponse:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    membership = await svc.update_member_role(org, user_id, payload.role, current_user)
    await db.refresh(membership, ["user"])
    return MembershipResponse(
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        role=membership.role,
        created_at=membership.created_at,
        name=membership.user.full_name if membership.user else None,
        email=membership.user.email if membership.user else None,
        avatar_url=membership.user.avatar_url if membership.user else None,
    )


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: str, user_id: str, current_user: CurrentUser, db: DBDep
) -> None:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    await svc.remove_member(org, user_id, current_user)
