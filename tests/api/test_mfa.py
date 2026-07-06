"""Tests for the MFA (TOTP) flow — setup, verify, disable, and validate during login."""

import pyotp
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    """Register + login, return access token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Secure1234!", "full_name": "Test User"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secure1234!"},
    )
    return res.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _valid_totp(secret: str) -> str:
    return pyotp.TOTP(secret).now()


# ── Setup ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mfa_setup(client: AsyncClient) -> None:
    token = await _register_and_login(client, "setup@example.com")
    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert "secret" in data
    assert "otpauth_uri" in data
    assert data["otpauth_uri"].startswith("otpauth://")


@pytest.mark.asyncio
async def test_mfa_setup_twice_fails(client: AsyncClient) -> None:
    token = await _register_and_login(client, "setup2@example.com")

    # First setup
    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    assert res.status_code == 200
    secret = res.json()["secret"]

    # Verify to activate
    code = _valid_totp(secret)
    res = await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))
    assert res.status_code == 204

    # Second setup should fail
    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    assert res.status_code == 400
    assert "already enabled" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mfa_setup_unauthenticated(client: AsyncClient) -> None:
    res = await client.post("/api/v1/mfa/setup")
    assert res.status_code == 401


# ── Verify ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mfa_verify(client: AsyncClient) -> None:
    token = await _register_and_login(client, "verify@example.com")

    # Setup
    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    secret = res.json()["secret"]

    # Verify with valid TOTP
    code = _valid_totp(secret)
    res = await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))
    assert res.status_code == 204

    # Confirm MFA is now active on the user
    me = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me.json()["mfa_enabled"] is True


@pytest.mark.asyncio
async def test_mfa_verify_invalid_code(client: AsyncClient) -> None:
    token = await _register_and_login(client, "verifybad@example.com")

    await client.post("/api/v1/mfa/setup", headers=auth_header(token))

    res = await client.post("/api/v1/mfa/verify?code=000000", headers=auth_header(token))
    assert res.status_code == 400
    assert "invalid" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mfa_verify_without_setup(client: AsyncClient) -> None:
    token = await _register_and_login(client, "verifyno@example.com")
    res = await client.post("/api/v1/mfa/verify?code=123456", headers=auth_header(token))
    assert res.status_code == 400
    assert "setup first" in res.json()["detail"].lower()


# ── Disable ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mfa_disable(client: AsyncClient) -> None:
    token = await _register_and_login(client, "disable@example.com")

    # Setup + verify
    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    secret = res.json()["secret"]
    code = _valid_totp(secret)
    await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))

    # Now disable
    code = _valid_totp(secret)
    res = await client.post(f"/api/v1/mfa/disable?code={code}", headers=auth_header(token))
    assert res.status_code == 204

    # Confirm MFA is off
    me = await client.get("/api/v1/auth/me", headers=auth_header(token))
    assert me.json()["mfa_enabled"] is False


@pytest.mark.asyncio
async def test_mfa_disable_invalid_code(client: AsyncClient) -> None:
    token = await _register_and_login(client, "disablebad@example.com")

    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    secret = res.json()["secret"]
    code = _valid_totp(secret)
    await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))

    res = await client.post("/api/v1/mfa/disable?code=000000", headers=auth_header(token))
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_mfa_disable_not_enabled(client: AsyncClient) -> None:
    token = await _register_and_login(client, "disableno@example.com")
    res = await client.post("/api/v1/mfa/disable?code=123456", headers=auth_header(token))
    assert res.status_code == 400
    assert "not enabled" in res.json()["detail"].lower()


# ── Login flow with MFA ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_returns_mfa_pending_when_mfa_enabled(client: AsyncClient) -> None:
    email = "mfa-login@example.com"
    password = "Secure1234!"
    token = await _register_and_login(client, email)

    # Setup + verify MFA
    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    secret = res.json()["secret"]
    code = _valid_totp(secret)
    await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))

    # Now login again — should get MFA pending token, not full tokens
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200
    data = res.json()
    assert "mfa_pending" in data
    assert "expires_in" in data
    assert data["expires_in"] == 300
    assert "access_token" not in data
    assert "user" not in data


@pytest.mark.asyncio
async def test_mfa_validate(client: AsyncClient) -> None:
    email = "validate@example.com"
    password = "Secure1234!"
    token = await _register_and_login(client, email)

    # Setup + verify MFA
    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    secret = res.json()["secret"]
    code = _valid_totp(secret)
    await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))

    # Login to get pending token
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    pending_token = res.json()["mfa_pending"]

    # Validate with valid TOTP
    code = _valid_totp(secret)
    res = await client.post(
        f"/api/v1/mfa/validate?code={code}",
        headers=auth_header(pending_token),
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_mfa_validate_invalid_code(client: AsyncClient) -> None:
    email = "validatebad@example.com"
    token = await _register_and_login(client, email)

    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    secret = res.json()["secret"]
    code = _valid_totp(secret)
    await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secure1234!"},
    )
    pending_token = res.json()["mfa_pending"]

    res = await client.post(
        "/api/v1/mfa/validate?code=000000",
        headers=auth_header(pending_token),
    )
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mfa_validate_with_access_token_fails(client: AsyncClient) -> None:
    email = "validatewrongtoken@example.com"
    token = await _register_and_login(client, email)

    res = await client.post("/api/v1/mfa/setup", headers=auth_header(token))
    secret = res.json()["secret"]
    code = _valid_totp(secret)
    await client.post(f"/api/v1/mfa/verify?code={code}", headers=auth_header(token))

    # Try /mfa/validate with an access token instead of a pending token
    code = _valid_totp(secret)
    res = await client.post(
        f"/api/v1/mfa/validate?code={code}",
        headers=auth_header(token),
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_mfa_validate_unauthenticated(client: AsyncClient) -> None:
    res = await client.post("/api/v1/mfa/validate?code=123456")
    assert res.status_code == 401


# ── Login without MFA still works ────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_without_mfa_returns_tokens_directly(client: AsyncClient) -> None:
    email = "no-mfa@example.com"
    password = "Secure1234!"
    await _register_and_login(client, email)

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "mfa_pending" not in data
    assert "user" in data
    assert "organizations" in data["user"]
    assert data["user"]["organizations"] == []
