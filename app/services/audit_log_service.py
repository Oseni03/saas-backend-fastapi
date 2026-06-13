"""
Audit log service — thin wrapper around AuditLogRepository.
Import this in route handlers to capture who did what.

Usage:
    await AuditLogService(db).log(
        action="org.member_invited",
        user_id=current_user.id,
        organization_id=org.id,
        resource_type="invitation",
        resource_id=invitation.id,
        request=request,
        meta={"email": payload.email, "role": payload.role},
    )
"""

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_log_repo import AuditLogRepository
from app.models.audit_log import AuditLog


class AuditLogService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = AuditLogRepository(db)

    async def log(
        self,
        action: str,
        user_id: str | None = None,
        organization_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        request: Request | None = None,
        meta: dict[str, Any] | None = None,
    ) -> AuditLog:
        ip_address: str | None = None
        user_agent: str | None = None

        if request:
            forwarded = request.headers.get("X-Forwarded-For")
            ip_address = (
                forwarded.split(",")[0].strip()
                if forwarded
                else (request.client.host if request.client else None)
            )
            user_agent = request.headers.get("User-Agent")

        return await self._repo.create(
            action=action,
            user_id=user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            meta=meta,
        )
