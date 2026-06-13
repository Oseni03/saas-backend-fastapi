"""
Notification service — create in-app notifications.
Call this from other services to fan out events to users.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.ulid import new_ulid
from app.models.notification import Notification


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: str,
        title: str,
        body: str,
        link: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Notification:
        notification = Notification(
            id=new_ulid(),
            user_id=user_id,
            title=title,
            body=body,
            link=link,
            meta=meta,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    # ── Convenience helpers ───────────────────────────────────────────

    async def notify_invitation_accepted(
        self, inviter_user_id: str, joiner_name: str, org_name: str, org_id: str
    ) -> Notification:
        return await self.create(
            user_id=inviter_user_id,
            title=f"{joiner_name} joined {org_name}",
            body=f"{joiner_name} accepted your invitation to join {org_name}.",
            link=f"/organizations/{org_id}/members",
            meta={"event": "invitation_accepted", "org_id": org_id},
        )

    async def notify_role_changed(
        self, user_id: str, new_role: str, org_name: str, org_id: str
    ) -> Notification:
        return await self.create(
            user_id=user_id,
            title=f"Your role in {org_name} was updated",
            body=f"You are now a {new_role} in {org_name}.",
            link=f"/organizations/{org_id}",
            meta={"event": "role_changed", "org_id": org_id, "new_role": new_role},
        )

    async def notify_plan_upgraded(
        self, user_id: str, plan: str, org_name: str, org_id: str
    ) -> Notification:
        return await self.create(
            user_id=user_id,
            title=f"{org_name} upgraded to {plan.title()}",
            body=f"Your organization is now on the {plan.title()} plan. Enjoy the new features!",
            link=f"/organizations/{org_id}/billing",
            meta={"event": "plan_upgraded", "org_id": org_id, "plan": plan},
        )
