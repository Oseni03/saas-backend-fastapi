"""
Organization service — create orgs, manage members, handle invitations.
"""

from datetime import UTC, datetime, timedelta

from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import project
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import generate_secure_token, hash_token
from app.lib.logger import logger
from app.lib.ulid import new_ulid
from app.models.invitation import Invitation, InvitationStatus
from app.models.membership import Membership, MemberRole
from app.models.organization import Organization, PlanTier
from app.models.user import User
from app.repositories.invitation_repo import InvitationRepository
from app.repositories.org_repo import OrganizationRepository
from app.repositories.user_repo import UserRepository
from app.schemas.organization import OrgCreateRequest, OrgUpdateRequest
from app.services.membership_policy import MembershipPolicy


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)
        self.inv_repo = InvitationRepository(db)

    # ── Org CRUD ──────────────────────────────────────────────────────

    async def create(self, payload: OrgCreateRequest, owner: User) -> Organization:
        base_slug = slugify(payload.name)
        slug = await self._unique_slug(base_slug)

        org = Organization(
            id=new_ulid(),
            name=payload.name,
            slug=slug,
            plan=PlanTier.FREE,
        )
        await self.org_repo.create(org)

        # Make the creator the owner
        membership = Membership(
            id=new_ulid(),
            user_id=owner.id,
            organization_id=org.id,
            role=MemberRole.OWNER,
        )
        self.db.add(membership)
        await self.db.flush()

        logger.info("org.created", org_id=org.id, owner_id=owner.id)
        return org

    async def update(
        self, org: Organization, payload: OrgUpdateRequest, actor: User
    ) -> Organization:
        await self._require_role(actor.id, org.id, MemberRole.ADMIN)

        if payload.name is not None:
            org.name = payload.name
        if payload.logo_url is not None:
            org.logo_url = str(payload.logo_url)

        return await self.org_repo.save(org)

    async def delete(self, org: Organization, actor: User) -> None:
        await self._require_role(actor.id, org.id, MemberRole.OWNER)
        await self.org_repo.delete(org)
        logger.info("org.deleted", org_id=org.id, actor_id=actor.id)

    async def list_for_user(self, user_id: str) -> list[Organization]:
        return await self.org_repo.list_for_user(user_id)

    # ── Members ───────────────────────────────────────────────────────

    async def list_members(self, org: Organization, actor: User) -> list[tuple[Membership, User]]:
        await self._require_role(actor.id, org.id, MemberRole.MEMBER)
        from sqlalchemy import select
        result = await self.db.execute(
            select(Membership, User)
            .join(User, Membership.user_id == User.id)
            .where(Membership.organization_id == org.id)
        )
        return list(result.all())

    async def update_member_role(
        self, org: Organization, target_user_id: str, new_role: MemberRole, actor: User
    ) -> Membership:
        await self._require_role(actor.id, org.id, MemberRole.ADMIN)

        from sqlalchemy import select
        result = await self.db.execute(
            select(Membership).where(
                Membership.user_id == target_user_id,
                Membership.organization_id == org.id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise NotFoundError("Member")

        # Can't change an owner's role unless you are also an owner
        if membership.role == MemberRole.OWNER:
            await self._require_role(actor.id, org.id, MemberRole.OWNER)

        membership.role = new_role
        await self.db.flush()
        return membership

    async def remove_member(
        self, org: Organization, target_user_id: str, actor: User
    ) -> None:
        if actor.id != target_user_id:
            await self._require_role(actor.id, org.id, MemberRole.ADMIN)

        from sqlalchemy import select, delete
        await self.db.execute(
            delete(Membership).where(
                Membership.user_id == target_user_id,
                Membership.organization_id == org.id,
            )
        )
        logger.info(
            "org.member_removed",
            org_id=org.id,
            target_user_id=target_user_id,
            actor_id=actor.id,
        )

    # ── Invitations ───────────────────────────────────────────────────

    async def list_invitations(self, org: Organization, actor: User) -> list[Invitation]:
        await self._require_role(actor.id, org.id, MemberRole.ADMIN)
        return await self.inv_repo.list_by_org(org.id)

    async def invite_member(
        self, org: Organization, email: str, role: MemberRole, actor: User
    ) -> tuple[Invitation, str]:
        await self._require_role(actor.id, org.id, MemberRole.ADMIN)

        email = email.lower().strip()

        existing = await self.inv_repo.get_pending_by_email_and_org(email, org.id)
        if existing:
            raise ConflictError("A pending invitation already exists for this email.")

        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            from sqlalchemy import select
            result = await self.db.execute(
                select(Membership).where(
                    Membership.user_id == existing_user.id,
                    Membership.organization_id == org.id,
                )
            )
            if result.scalar_one_or_none():
                raise ConflictError("This user is already a member of the organization.")

        raw_token = generate_secure_token()
        invitation = Invitation(
            id=new_ulid(),
            organization_id=org.id,
            email=email,
            role=role.value,
            token=hash_token(raw_token),
            invited_by_id=actor.id,
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(days=project.expiry.invitation_days),
        )
        await self.inv_repo.create(invitation)

        logger.info("org.invitation_sent", org_id=org.id, email=email, actor_id=actor.id)
        return invitation, raw_token

    async def revoke_invitation(
        self, org: Organization, invitation_id: str, actor: User
    ) -> Invitation:
        await self._require_role(actor.id, org.id, MemberRole.ADMIN)

        invitation = await self.inv_repo.get_by_id(invitation_id)
        if not invitation or invitation.organization_id != org.id:
            raise NotFoundError("Invitation")
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError(f"Cannot revoke an invitation that is {invitation.status.value}.")

        invitation.status = InvitationStatus.REVOKED
        await self.inv_repo.save(invitation)

        logger.info(
            "org.invitation_revoked",
            org_id=org.id,
            invitation_id=invitation_id,
            email=invitation.email,
            actor_id=actor.id,
        )
        return invitation

    async def accept_invitation(self, token: str, user: User) -> Organization:
        hashed = hash_token(token)
        invitation = await self.inv_repo.get_by_token(hashed)
        if not invitation:
            raise BadRequestError("Invalid or expired invitation.")
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError(f"Invitation is {invitation.status.value}.")
        if invitation.expires_at < datetime.now(UTC):
            invitation.status = InvitationStatus.EXPIRED
            await self.inv_repo.save(invitation)
            raise BadRequestError("Invitation has expired.")
        if invitation.email != user.email:
            raise ForbiddenError("This invitation was sent to a different email address.")

        # Create membership
        membership = Membership(
            id=new_ulid(),
            user_id=user.id,
            organization_id=invitation.organization_id,
            role=invitation.role,  # type: ignore[arg-type]
        )
        self.db.add(membership)

        invitation.status = InvitationStatus.ACCEPTED
        await self.inv_repo.save(invitation)

        org = await self.org_repo.get_by_id(invitation.organization_id)
        logger.info("org.invitation_accepted", org_id=invitation.organization_id, user_id=user.id)
        return org  # type: ignore[return-value]

    # ── Internal ──────────────────────────────────────────────────────

    async def _require_role(
        self, user_id: str, org_id: str, min_role: MemberRole
    ) -> Membership:
        from sqlalchemy import select

        result = await self.db.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.organization_id == org_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise ForbiddenError("You are not a member of this organization.")

        MembershipPolicy.ensure_role(membership, min_role)
        return membership

    async def _unique_slug(self, base: str) -> str:
        slug = base
        counter = 1
        while await self.org_repo.get_by_slug(slug):
            slug = f"{base}-{counter}"
            counter += 1
        return slug
