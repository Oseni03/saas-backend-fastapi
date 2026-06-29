"""
Auth service — registration, login, token refresh, email verification,
password reset, and OAuth flows.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
    verify_refresh_token,
    verify_token_hash,
    revoke_refresh_token,
)
from app.lib.email import send_password_reset_email, send_welcome_email
from app.lib.logger import logger
from app.lib.ulid import new_ulid
from app.models.user import OAuthProvider, User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenPair,
)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    # ── Register ──────────────────────────────────────────────────────

    async def register(self, payload: RegisterRequest) -> tuple[User, TokenPair, str]:
        existing = await self.user_repo.get_by_email(payload.email)
        if existing:
            raise ConflictError("An account with this email already exists.")

        verification_token = generate_secure_token()
        user = User(
            id=new_ulid(),
            email=payload.email.lower().strip(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            is_active=True,
            is_verified=False,
            verification_token=hash_token(verification_token),
        )
        await self.user_repo.create(user)

        logger.info("auth.registered", user_id=user.id, email=user.email)
        return user, self._issue_tokens(user.id), verification_token

    # ── Login ─────────────────────────────────────────────────────────

    async def login(self, payload: LoginRequest) -> TokenPair:
        user = await self.user_repo.get_by_email(payload.email)
        if not user or not user.hashed_password:
            raise UnauthorizedError("Invalid email or password.")
        if not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("Your account has been deactivated.")

        logger.info("auth.login", user_id=user.id)
        return self._issue_tokens(user.id)

    # ── Refresh ───────────────────────────────────────────────────────

    async def refresh(self, refresh_token: str) -> TokenPair:
        from jose import JWTError

        try:
            user_id = await verify_refresh_token(refresh_token)
        except JWTError as exc:
            raise UnauthorizedError("Invalid or expired refresh token.") from exc

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")

        return self._issue_tokens(user.id)
    
    # ── Logout ────────────────────────────────────────────────────────

    async def logout(self, refresh_token: str) -> None:
        """Invalidate a refresh token (blacklisting)."""
        from jose import JWTError

        try:
            user_id = await verify_refresh_token(refresh_token)
            # Revoke the token (implementation depends on your security module)
            await revoke_refresh_token(refresh_token)   # e.g., add to Redis blacklist or DB
            logger.info("auth.logout", user_id=user_id)
        except JWTError:
            # Silent fail for security (don't reveal if token was valid)
            pass
        except Exception as exc:
            logger.warning("auth.logout_failed", error=str(exc))

    # ── Email verification ────────────────────────────────────────────

    async def verify_email(self, token: str) -> User:
        hashed = hash_token(token)
        user = await self.user_repo.get_by_verification_token(hashed)
        if not user:
            raise BadRequestError("Invalid or expired verification token.")

        user.is_verified = True
        user.verification_token = None
        await self.user_repo.save(user)

        send_welcome_email(user.email, user.full_name or "")
        logger.info("auth.email_verified", user_id=user.id)
        return user

    # ── Password reset ────────────────────────────────────────────────

    async def request_password_reset(self, email: str) -> None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal whether the email exists
            return

        reset_token = generate_secure_token()
        user.reset_token = hash_token(reset_token)
        await self.user_repo.save(user)

        send_password_reset_email(user.email, reset_token)
        logger.info("auth.password_reset_requested", user_id=user.id)

    async def reset_password(self, token: str, new_password: str) -> User:
        hashed = hash_token(token)
        user = await self.user_repo.get_by_reset_token(hashed)
        if not user:
            raise BadRequestError("Invalid or expired reset token.")

        user.hashed_password = hash_password(new_password)
        user.reset_token = None
        await self.user_repo.save(user)

        logger.info("auth.password_reset", user_id=user.id)
        return user

    # ── OAuth ─────────────────────────────────────────────────────────

    async def oauth_login_or_register(
        self,
        provider: OAuthProvider,
        provider_id: str,
        email: str,
        full_name: str | None,
        avatar_url: str | None,
    ) -> TokenPair:
        user = await self.user_repo.get_by_oauth(provider, provider_id)

        if not user:
            # Check if an account exists with this email
            user = await self.user_repo.get_by_email(email)
            if user:
                # Link OAuth to existing account
                user.oauth_provider = provider
                user.oauth_provider_id = provider_id
                user.is_verified = True
                await self.user_repo.save(user)
            else:
                # Create new user
                user = User(
                    id=new_ulid(),
                    email=email.lower().strip(),
                    full_name=full_name,
                    avatar_url=avatar_url,
                    is_active=True,
                    is_verified=True,  # OAuth emails are pre-verified
                    oauth_provider=provider,
                    oauth_provider_id=provider_id,
                )
                await self.user_repo.create(user)
                logger.info("auth.oauth_registered", user_id=user.id, provider=provider)

        logger.info("auth.oauth_login", user_id=user.id, provider=provider)
        return self._issue_tokens(user.id)

    # ── Internal ──────────────────────────────────────────────────────

    def _issue_tokens(self, user_id: str) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
            token_type="bearer",
        )
