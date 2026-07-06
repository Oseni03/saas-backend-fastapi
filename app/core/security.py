import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import project, settings
from app.lib.redis import set_with_ttl, get_value


# ── Password ──────────────────────────────────────────────────────────


def _prehash(password: str) -> bytes:
    """bcrypt is limited to 72 bytes; SHA-256 pre-hash avoids that constraint."""
    return hashlib.sha256(password.encode()).hexdigest().encode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prehash(plain), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────


def create_mfa_pending_token(subject: str) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": project.jwt.mfa_pending_token_type,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(seconds=project.mfa.pending_expires_in_seconds),
    }
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=project.jwt.algorithm)


def verify_mfa_pending_token(token: str) -> str:
    """Returns user_id or raises JWTError."""
    payload = decode_token(token)
    if payload.get("type") != project.jwt.mfa_pending_token_type:
        raise JWTError("Not an MFA pending token")
    sub: str = payload["sub"]
    return sub


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": project.jwt.access_token_type,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=project.jwt.algorithm)


def create_refresh_token(subject: str) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": project.jwt.refresh_token_type,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=project.jwt.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Raises JWTError on invalid / expired tokens."""
    return jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[project.jwt.algorithm])


def verify_access_token(token: str) -> str:
    """Returns user_id or raises JWTError."""
    payload = decode_token(token)
    if payload.get("type") != project.jwt.access_token_type:
        raise JWTError("Not an access token")
    sub: str = payload["sub"]
    return sub


async def verify_refresh_token(token: str) -> str:
    """Returns user_id or raises JWTError. Also checks blacklist."""
    # First check if token is blacklisted
    if (await is_token_blacklisted(token)):  # Note: this makes the function async
        raise JWTError("Token has been revoked")

    payload = decode_token(token)
    if payload.get("type") != project.jwt.refresh_token_type:
        raise JWTError("Not a refresh token")
    sub: str = payload["sub"]
    return sub


# ── Token Revocation (Blacklisting) ───────────────────────────────────


async def revoke_refresh_token(refresh_token: str) -> None:
    """
    Blacklist a refresh token using the centralized Redis helpers.
    """
    try:
        # Decode to get accurate expiration time
        payload = decode_token(refresh_token)
        exp_timestamp = payload.get("exp")

        if exp_timestamp:
            expires_in = max(0, exp_timestamp - int(datetime.now(UTC).timestamp()))
        else:
            expires_in = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600  # fallback

        if expires_in > 0:
            await set_with_ttl(
                key=f"token_blacklist:{refresh_token}",
                value="revoked",
                ttl_seconds=expires_in,
            )
    except Exception as e:
        # Log but don't fail logout
        import logging
        logging.warning(f"Failed to revoke refresh token: {e}")


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted using Redis helper."""
    try:
        result = await get_value(f"token_blacklist:{token}")
        return result is not None
    except Exception:
        # Fail open (allow the token) if Redis is down
        import logging
        logging.error("Redis blacklist check failed - allowing token")
        return False


# ── One-time tokens (email verification, invites, password reset) ─────


def generate_secure_token(nbytes: int = project.secure_token_bytes) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Store hashed version in DB; compare with verify_token."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, hashed: str) -> bool:
    return hash_token(token) == hashed
