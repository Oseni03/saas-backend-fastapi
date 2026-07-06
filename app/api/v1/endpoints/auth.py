from fastapi import APIRouter, BackgroundTasks, status

from app.api.deps import CurrentUser, DBDep
from app.lib.email import send_verification_email
from app.lib.logger import logger
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MfaPendingResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    SignupResponse,
    TokenPair,
    VerifyEmailRequest,
    LogoutRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService, LoginSuccess

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DBDep, background_tasks: BackgroundTasks) -> SignupResponse:
    """Register a new user. Sends a verification email. Returns user + tokens."""
    user, tokens, verification_token = await AuthService(db).register(payload)
    background_tasks.add_task(_send_verification_email, user.email, user.full_name, verification_token)
    return SignupResponse(
        user=UserResponse.model_validate(user),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
    )


def _send_verification_email(to: str, full_name: str | None, token: str) -> None:
    try:
        send_verification_email(to, full_name or "", token)
    except Exception:
        logger.exception("Failed to send verification email", to=to)


@router.post("/login", response_model=LoginResponse | MfaPendingResponse)
async def login(payload: LoginRequest, db: DBDep) -> LoginResponse | MfaPendingResponse:
    """Authenticate with email + password. Returns tokens+user or MFA pending response."""
    result = await AuthService(db).login(payload)
    if isinstance(result, LoginSuccess):
        return LoginResponse(
            user=UserResponse.model_validate(result.user),
            access_token=result.token_pair.access_token,
            refresh_token=result.token_pair.refresh_token,
            token_type=result.token_pair.token_type,
        )
    return result


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    payload: LogoutRequest,
    db: DBDep,
):
    """
    Logout by invalidating the refresh token.
    """
    auth_service = AuthService(db)
    await auth_service.logout(payload.refresh_token)
    return {"message": "Successfully logged out."}


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
