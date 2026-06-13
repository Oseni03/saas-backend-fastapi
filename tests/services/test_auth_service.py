"""
Unit tests for AuthService — test business logic directly without HTTP.
"""

import pytest
from unittest.mock import patch

from app.core.exceptions import ConflictError, UnauthorizedError
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_register_creates_user(db_session) -> None:
    with patch("app.services.auth_service.send_verification_email"):
        svc = AuthService(db_session)
        user = await svc.register(
            RegisterRequest(email="unit@example.com", password="Secure1234!")
        )
    assert user.email == "unit@example.com"
    assert user.is_verified is False
    assert user.hashed_password is not None
    # Raw password must NOT be stored
    assert user.hashed_password != "Secure1234!"


@pytest.mark.asyncio
async def test_register_duplicate_raises(db_session) -> None:
    with patch("app.services.auth_service.send_verification_email"):
        svc = AuthService(db_session)
        await svc.register(RegisterRequest(email="dup@example.com", password="Secure1234!"))
        with pytest.raises(ConflictError):
            await svc.register(
                RegisterRequest(email="dup@example.com", password="Secure1234!")
            )


@pytest.mark.asyncio
async def test_login_wrong_password_raises(db_session) -> None:
    with patch("app.services.auth_service.send_verification_email"):
        svc = AuthService(db_session)
        await svc.register(RegisterRequest(email="login@example.com", password="Secure1234!"))

    with pytest.raises(UnauthorizedError):
        await AuthService(db_session).login(
            LoginRequest(email="login@example.com", password="WrongPass1!")
        )


@pytest.mark.asyncio
async def test_login_returns_token_pair(db_session) -> None:
    with patch("app.services.auth_service.send_verification_email"):
        svc = AuthService(db_session)
        await svc.register(RegisterRequest(email="tok@example.com", password="Secure1234!"))

    tokens = await AuthService(db_session).login(
        LoginRequest(email="tok@example.com", password="Secure1234!")
    )
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"


@pytest.mark.asyncio
async def test_verify_email(db_session) -> None:
    raw_token = None

    def capture_token(email, name, token):
        nonlocal raw_token
        raw_token = token

    with patch("app.services.auth_service.send_verification_email", side_effect=capture_token):
        svc = AuthService(db_session)
        user = await svc.register(
            RegisterRequest(email="verify@example.com", password="Secure1234!")
        )

    assert raw_token is not None
    verified_user = await AuthService(db_session).verify_email(raw_token)
    assert verified_user.is_verified is True
    assert verified_user.verification_token is None


@pytest.mark.asyncio
async def test_password_reset_flow(db_session) -> None:
    with patch("app.services.auth_service.send_verification_email"):
        await AuthService(db_session).register(
            RegisterRequest(email="reset@example.com", password="Secure1234!")
        )

    reset_token = None

    def capture_reset(email, token):
        nonlocal reset_token
        reset_token = token

    with patch("app.services.auth_service.send_password_reset_email", side_effect=capture_reset):
        await AuthService(db_session).request_password_reset("reset@example.com")

    assert reset_token is not None
    user = await AuthService(db_session).reset_password(reset_token, "NewSecure1234!")
    assert user.reset_token is None

    # Old password should no longer work
    with pytest.raises(UnauthorizedError):
        await AuthService(db_session).login(
            LoginRequest(email="reset@example.com", password="Secure1234!")
        )

    # New password should work
    tokens = await AuthService(db_session).login(
        LoginRequest(email="reset@example.com", password="NewSecure1234!")
    )
    assert tokens.access_token
