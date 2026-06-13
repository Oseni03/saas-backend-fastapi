"""
Admin endpoints — superuser-only operations.
Docs are hidden in production; accessible at /docs only in dev/staging.
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DBDep, get_superuser
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrgResponse
from app.schemas.user import UserResponse
from fastapi import Depends

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_superuser)],
)


@router.get("/stats")
async def platform_stats(db: DBDep) -> dict:
    """High-level platform statistics."""
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    org_count = (await db.execute(select(func.count()).select_from(Organization))).scalar()
    verified_count = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_verified == True)  # noqa: E712
        )
    ).scalar()

    return {
        "users": {"total": user_count, "verified": verified_count},
        "organizations": {"total": org_count},
    }


@router.get("/users", response_model=list[UserResponse])
async def list_all_users(db: DBDep, limit: int = 50, offset: int = 0) -> list[UserResponse]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.get("/organizations", response_model=list[OrgResponse])
async def list_all_orgs(db: DBDep, limit: int = 50, offset: int = 0) -> list[OrgResponse]:
    result = await db.execute(
        select(Organization).order_by(Organization.created_at.desc()).limit(limit).offset(offset)
    )
    return [OrgResponse.model_validate(o) for o in result.scalars().all()]


@router.patch("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(user_id: str, db: DBDep) -> UserResponse:
    from app.repositories.user_repo import UserRepository
    from app.core.exceptions import NotFoundError

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundError("User")
    user.is_active = False
    await repo.save(user)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(user_id: str, db: DBDep) -> UserResponse:
    from app.repositories.user_repo import UserRepository
    from app.core.exceptions import NotFoundError

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundError("User")
    user.is_active = True
    await repo.save(user)
    return UserResponse.model_validate(user)
