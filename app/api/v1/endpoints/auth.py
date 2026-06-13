from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBDep
from app.schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DBDep) -> UserResponse:
    """Register a new user. Sends a verification email."""
    user = await AuthService(db).register(payload)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: DBDep) -> TokenPair:
    """Authenticate with email + password. Returns access + refresh tokens."""
    return await AuthService(db).login(payload)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: DBDep) -> TokenPair:
    """Exchange a refresh token for a new token pair."""
    return await AuthService(db).refresh(payload.refresh_token)


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(payload: VerifyEmailRequest, db: DBDep) -> UserResponse:
    """Verify email address with the token sent on registration."""
    user = await AuthService(db).verify_email(payload.token)
    return UserResponse.model_validate(user)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(payload: PasswordResetRequest, db: DBDep) -> dict:
    """Request a password reset email. Always returns 202 to prevent email enumeration."""
    await AuthService(db).request_password_reset(payload.email)
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password", response_model=UserResponse)
async def reset_password(payload: PasswordResetConfirm, db: DBDep) -> UserResponse:
    """Complete password reset with the token from the email."""
    user = await AuthService(db).reset_password(payload.token, payload.new_password)
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse.model_validate(current_user)
