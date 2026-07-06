"""MFA (TOTP) endpoints.

Flow:
  1. POST /mfa/setup      → generates secret, returns otpauth URI
  2. POST /mfa/verify     → confirms TOTP code, activates MFA
  3. POST /mfa/disable    → disables MFA (requires current TOTP code)
  4. POST /mfa/validate   → called during login when MFA is active
"""

import pyotp
from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBDep, MfaPendingUser
from app.config import project
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenPair

router = APIRouter(prefix="/mfa", tags=["mfa"])


def _get_totp(secret: str, email: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret, issuer=project.mfa.issuer_name, name=email)


@router.post("/setup")
async def setup_mfa(current_user: CurrentUser, db: DBDep) -> dict:
    """Generate a new MFA secret and return the provisioning URI."""
    if current_user.mfa_enabled:
        raise BadRequestError("MFA is already enabled on your account.")

    secret = pyotp.random_base32()
    totp = _get_totp(secret, current_user.email)
    uri = totp.provisioning_uri()

    # Temporarily store the unconfirmed secret (user must verify before it's active)
    # In a real impl you'd cache this in Redis with a TTL instead of the DB
    current_user.mfa_secret = secret
    await UserRepository(db).save(current_user)

    return {
        "secret": secret,
        "otpauth_uri": uri,
        "message": "Enter the secret in your authenticator app, "
                   "then call /mfa/verify with a valid code.",
    }


@router.post("/verify", status_code=status.HTTP_204_NO_CONTENT)
async def verify_mfa(code: str, current_user: CurrentUser, db: DBDep) -> None:
    """Confirm the TOTP code to activate MFA."""
    if not current_user.mfa_secret:
        raise BadRequestError("Call /mfa/setup first.")
    if current_user.mfa_enabled:
        raise BadRequestError("MFA is already enabled.")

    totp = _get_totp(current_user.mfa_secret, current_user.email)
    if not totp.verify(code, valid_window=project.mfa.valid_window):
        raise BadRequestError("Invalid or expired TOTP code.")

    current_user.mfa_enabled = True
    await UserRepository(db).save(current_user)


@router.post("/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_mfa(code: str, current_user: CurrentUser, db: DBDep) -> None:
    """Disable MFA. Requires a valid current TOTP code."""
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        raise BadRequestError("MFA is not enabled on your account.")

    totp = _get_totp(current_user.mfa_secret, current_user.email)
    if not totp.verify(code, valid_window=project.mfa.valid_window):
        raise UnauthorizedError("Invalid TOTP code.")

    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    await UserRepository(db).save(current_user)


@router.post("/validate")
async def validate_mfa_code(code: str, user: MfaPendingUser) -> TokenPair:
    """
    Validate a TOTP code during login.
    Frontend calls this after obtaining a short-lived 'mfa_pending' token
    from /auth/login. Returns a full token pair on success.
    """
    if not user.mfa_enabled or not user.mfa_secret:
        raise BadRequestError("MFA is not enabled on your account.")

    totp = _get_totp(user.mfa_secret, user.email)
    if not totp.verify(code, valid_window=project.mfa.valid_window):
        raise UnauthorizedError("Invalid or expired TOTP code.")

    from app.core.security import create_access_token, create_refresh_token
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type=project.token_type,
    )
