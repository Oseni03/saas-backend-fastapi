from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBDep, VerifiedUser
from app.core.exceptions import NotFoundError
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

@router.post("/{org_id}/invitations", status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: str, payload: InviteMemberRequest, current_user: CurrentUser, db: DBDep
) -> dict:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    await svc.invite_member(org, payload.email, payload.role, current_user)
    return {"message": "Invitation sent."}


@router.post("/invitations/accept", response_model=OrgResponse)
async def accept_invitation(
    payload: AcceptInvitationRequest, current_user: CurrentUser, db: DBDep
) -> OrgResponse:
    org = await OrganizationService(db).accept_invitation(payload.token, current_user)
    return OrgResponse.model_validate(org)


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
    return MembershipResponse.model_validate(membership)


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: str, user_id: str, current_user: CurrentUser, db: DBDep
) -> None:
    svc = OrganizationService(db)
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    await svc.remove_member(org, user_id, current_user)
