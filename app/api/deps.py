"""
Shared FastAPI dependencies.
Imported via `Depends()` in route handlers.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import project
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.db.session import get_db
from app.models.membership import MemberRole, Membership
from app.models.organization import Organization
from app.models.user import User
from app.repositories.org_repo import OrganizationRepository
from app.repositories.user_repo import UserRepository
from app.core.security import verify_access_token, verify_mfa_pending_token

bearer_scheme = HTTPBearer(auto_error=False)


# ── DB ────────────────────────────────────────────────────────────────

DBDep = Annotated[AsyncSession, Depends(get_db)]


# ── Current user ──────────────────────────────────────────────────────

async def get_current_user(
    db: DBDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if not credentials:
        raise UnauthorizedError()

    try:
        user_id = verify_access_token(credentials.credentials)
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc

    user = await UserRepository(db).get_by_id_with_orgs(user_id)
    if not user:
        raise UnauthorizedError("User not found.")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_mfa_pending_user(
    db: DBDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if not credentials:
        raise UnauthorizedError()

    try:
        user_id = verify_mfa_pending_token(credentials.credentials)
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired MFA pending token.") from exc

    user = await UserRepository(db).get_by_id_with_orgs(user_id)
    if not user:
        raise UnauthorizedError("User not found.")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive.")
    return user


MfaPendingUser = Annotated[User, Depends(get_mfa_pending_user)]


async def get_verified_user(current_user: CurrentUser) -> User:
    if not current_user.is_verified:
        raise ForbiddenError("Please verify your email address before continuing.")
    return current_user


VerifiedUser = Annotated[User, Depends(get_verified_user)]


async def get_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise ForbiddenError("Superuser access required.")
    return current_user


# ── Organization context ──────────────────────────────────────────────

async def get_current_org(
    org_id: str,
    db: DBDep,
    current_user: CurrentUser,
) -> Organization:
    org = await OrganizationRepository(db).get_by_id(org_id)
    if not org:
        raise NotFoundError("Organization")
    return org


CurrentOrg = Annotated[Organization, Depends(get_current_org)]


async def get_org_member(
    org: CurrentOrg,
    db: DBDep,
    current_user: CurrentUser,
) -> Membership:
    from sqlalchemy import select
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == current_user.id,
            Membership.organization_id == org.id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise ForbiddenError("You are not a member of this organization.")
    return membership


OrgMember = Annotated[Membership, Depends(get_org_member)]


def require_org_role(*roles: MemberRole):
    """Factory: returns a dependency that enforces a minimum role."""

    async def _check(membership: OrgMember) -> Membership:
        required = max(project.role_rank[r.name] for r in roles)
        if project.role_rank[membership.role.name] < required:
            raise ForbiddenError("You do not have sufficient permissions.")
        return membership

    return Depends(_check)


# ── Request metadata (for audit logs) ────────────────────────────────

def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("User-Agent")
