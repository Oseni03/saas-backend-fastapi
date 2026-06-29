from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel

from app.models.membership import MemberRole
from app.models.organization import PlanTier
from app.models.invitation import InvitationStatus


class OrgCreateRequest(BaseModel):
    name: str


class OrgUpdateRequest(BaseModel):
    name: str | None = None
    logo_url: AnyHttpUrl | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: str | None
    plan: PlanTier
    created_at: datetime

    model_config = {"from_attributes": True}


class MembershipResponse(BaseModel):
    user_id: str
    organization_id: str
    role: MemberRole
    created_at: datetime
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: datetime

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str
    role: MemberRole = MemberRole.MEMBER


class UpdateMemberRoleRequest(BaseModel):
    role: MemberRole


class AcceptInvitationRequest(BaseModel):
    token: str


class BillingInitSchema(BaseModel):
    plan: PlanTier
    callback_url: str


class BillingVerifyResponse(BaseModel):
    plan: PlanTier
    organization_id: str
