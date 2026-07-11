import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.invitation import Invitation
    from app.models.subscription import Subscription
    from app.models.audit_log import AuditLog


class PlanTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)  # ULID
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    plan: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, values_callable=lambda obj: [e.value for e in obj]),
        default=PlanTier.FREE,
        nullable=False,
    )

    # Paystack
    paystack_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Relationships
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="organization", uselist=False
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="organization")

    @property
    def member_count(self) -> int:
        return len(self.memberships)

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug}>"
