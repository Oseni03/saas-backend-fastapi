from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBDep
from app.core.exceptions import UnauthorizedError
from app.core.security import hash_password, verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.user import ChangePasswordRequest, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdateRequest, current_user: CurrentUser, db: DBDep
) -> UserResponse:
    repo = UserRepository(db)
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    user = await repo.save(current_user)
    return UserResponse.model_validate(user)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, db: DBDep
) -> None:
    if not current_user.hashed_password:
        raise UnauthorizedError("OAuth accounts cannot change passwords directly.")
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise UnauthorizedError("Current password is incorrect.")
    current_user.hashed_password = hash_password(payload.new_password)
    await UserRepository(db).save(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(current_user: CurrentUser, db: DBDep) -> None:
    """Soft-delete: deactivate the user account."""
    current_user.is_active = False
    await UserRepository(db).save(current_user)
