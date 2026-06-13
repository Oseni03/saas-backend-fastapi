"""
Seed script for local development.
Usage: python scripts/seed.py
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import hash_password
from app.lib.ulid import new_ulid
from app.models.membership import Membership, MemberRole
from app.models.organization import Organization, PlanTier
from app.models.user import User

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSession_ = async_sessionmaker(engine, expire_on_commit=False)


async def seed() -> None:
    async with AsyncSession_() as session:
        # Admin user
        admin = User(
            id=new_ulid(),
            email="admin@example.com",
            hashed_password=hash_password("Admin1234!"),
            full_name="Admin User",
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        session.add(admin)

        # Regular user
        member = User(
            id=new_ulid(),
            email="member@example.com",
            hashed_password=hash_password("Member1234!"),
            full_name="Regular Member",
            is_active=True,
            is_verified=True,
        )
        session.add(member)

        await session.flush()

        # Organization
        org = Organization(
            id=new_ulid(),
            name="Acme Corp",
            slug="acme-corp",
            plan=PlanTier.FREE,
        )
        session.add(org)
        await session.flush()

        # Memberships
        session.add(
            Membership(
                id=new_ulid(),
                user_id=admin.id,
                organization_id=org.id,
                role=MemberRole.OWNER,
            )
        )
        session.add(
            Membership(
                id=new_ulid(),
                user_id=member.id,
                organization_id=org.id,
                role=MemberRole.MEMBER,
            )
        )

        await session.commit()
        print("✅ Seed data created successfully.")
        print(f"   Admin:  admin@example.com / Admin1234!")
        print(f"   Member: member@example.com / Member1234!")
        print(f"   Org:    {org.name} (slug: {org.slug})")


if __name__ == "__main__":
    asyncio.run(seed())
