from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.membership import Membership
from app.models.organization import Organization


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, org_id: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization)
            .options(selectinload(Organization.memberships))
            .where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_paystack_customer_id(self, customer_code: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.paystack_customer_id == customer_code)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[Organization]:
        result = await self.db.execute(
            select(Organization)
            .options(selectinload(Organization.memberships))
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create(self, org: Organization) -> Organization:
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def save(self, org: Organization) -> Organization:
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def delete(self, org: Organization) -> None:
        await self.db.delete(org)
        await self.db.flush()
