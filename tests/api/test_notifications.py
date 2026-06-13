"""Tests for the notifications API."""

import pytest
from httpx import AsyncClient

from app.lib.ulid import new_ulid
from app.models.notification import Notification


async def _login(client: AsyncClient, email: str = "notify@example.com") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Secure1234!"},
    )
    return res.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient) -> None:
    token = await _login(client)
    res = await client.get("/api/v1/notifications", headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_notification_read(client: AsyncClient, db_session) -> None:
    token = await _login(client, "notif2@example.com")

    # Get user ID from /me
    me_res = await client.get("/api/v1/users/me", headers=auth(token))
    user_id = me_res.json()["id"]

    # Inject a notification directly
    notif = Notification(
        id=new_ulid(),
        user_id=user_id,
        title="Hello",
        body="You have a new message.",
        is_read=False,
    )
    db_session.add(notif)
    await db_session.flush()

    # List — should show 1 unread
    list_res = await client.get("/api/v1/notifications", headers=auth(token))
    assert list_res.json()["unread_count"] == 1

    # Mark read
    mark_res = await client.post(
        f"/api/v1/notifications/{notif.id}/read", headers=auth(token)
    )
    assert mark_res.status_code == 204

    # Now unread_count should be 0
    list_res2 = await client.get("/api/v1/notifications", headers=auth(token))
    assert list_res2.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, db_session) -> None:
    token = await _login(client, "notif3@example.com")
    me_res = await client.get("/api/v1/users/me", headers=auth(token))
    user_id = me_res.json()["id"]

    for i in range(3):
        db_session.add(
            Notification(
                id=new_ulid(),
                user_id=user_id,
                title=f"Notification {i}",
                body="Body",
                is_read=False,
            )
        )
    await db_session.flush()

    res = await client.post("/api/v1/notifications/read-all", headers=auth(token))
    assert res.status_code == 204

    list_res = await client.get("/api/v1/notifications", headers=auth(token))
    assert list_res.json()["unread_count"] == 0
