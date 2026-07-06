import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "Secure1234!",
            "full_name": "Test User",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["is_verified"] is False
    assert data["user"]["organizations"] == []
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "Secure1234!"}
    await client.post("/api/v1/auth/register", json=payload)
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "Secure1234!"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "Secure1234!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data
    assert "organizations" in data["user"]
    assert data["user"]["organizations"] == []


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bad@example.com", "password": "Secure1234!"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "bad@example.com", "password": "WrongPassword1!"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "Secure1234!"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "Secure1234!"},
    )
    token = login_res.json()["access_token"]
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me@example.com"
    assert "organizations" in data
    assert isinstance(data["organizations"], list)


@pytest.mark.asyncio
async def test_register_returns_tokens(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "tokens@example.com", "password": "Secure1234!"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == "tokens@example.com"
    assert data["user"]["organizations"] == []
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "Secure1234!"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "Secure1234!"},
    )
    refresh_token = login_res.json()["refresh_token"]
    res = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
