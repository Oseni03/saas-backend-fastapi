from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.membership import Membership
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_id_with_orgs(self, user_id: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.memberships).selectinload(Membership.organization))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_oauth(self, provider: str, provider_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_provider_id == provider_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, hashed_token: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.verification_token == hashed_token)
        )
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, hashed_token: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.reset_token == hashed_token)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def save(self, user: User) -> User:
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()
