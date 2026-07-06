from typing import Any

from datetime import datetime

from pydantic import BaseModel, EmailStr, model_validator

from app.models.membership import MemberRole
from app.models.organization import PlanTier
from app.models.user import User


class UserOrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: str | None
    plan: PlanTier
    role: MemberRole
    created_at: datetime


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None
    avatar_url: str | None
    is_verified: bool
    is_active: bool
    mfa_enabled: bool
    created_at: datetime
    organizations: list[UserOrgResponse] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def load_organizations(cls, data: Any) -> Any:
        if isinstance(data, User) and not isinstance(data, dict):
            memberships = data.memberships or []
            data.organizations = [
                UserOrgResponse(
                    id=m.organization.id,
                    name=m.organization.name,
                    slug=m.organization.slug,
                    logo_url=m.organization.logo_url,
                    plan=m.organization.plan,
                    role=m.role,
                    created_at=m.organization.created_at,
                )
                for m in memberships
                if m.organization
            ]
        return data


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
