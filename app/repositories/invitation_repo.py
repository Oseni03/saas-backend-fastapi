from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation, InvitationStatus


class InvitationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_token(self, token: str) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(Invitation.token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, invitation_id: str) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(Invitation.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_by_email_and_org(
        self, email: str, org_id: str
    ) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(
                Invitation.email == email.lower(),
                Invitation.organization_id == org_id,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(self, org_id: str) -> list[Invitation]:
        result = await self.db.execute(
            select(Invitation)
            .where(Invitation.organization_id == org_id)
            .order_by(Invitation.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, invitation: Invitation) -> Invitation:
        self.db.add(invitation)
        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation

    async def save(self, invitation: Invitation) -> Invitation:
        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation
