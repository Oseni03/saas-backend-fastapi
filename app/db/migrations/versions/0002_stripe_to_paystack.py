"""stripe to paystack

Revision ID: 0002_stripe_to_paystack
Revises: 0001_initial
Create Date: 2024-06-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_stripe_to_paystack"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # organizations: stripe_customer_id → paystack_customer_id
    op.alter_column("organizations", "stripe_customer_id",
                     new_column_name="paystack_customer_id")
    op.drop_index("ix_organizations_stripe_customer_id", table_name="organizations")
    op.create_index(
        "ix_organizations_paystack_customer_id",
        "organizations",
        ["paystack_customer_id"],
        unique=True,
    )

    # subscriptions: stripe_subscription_id → paystack_sub_code
    op.alter_column("subscriptions", "stripe_subscription_id",
                     new_column_name="paystack_sub_code")
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.create_index(
        "ix_subscriptions_paystack_sub_code",
        "subscriptions",
        ["paystack_sub_code"],
        unique=True,
    )

    # subscriptions: stripe_price_id → paystack_plan_code
    op.alter_column("subscriptions", "stripe_price_id",
                     new_column_name="paystack_plan_code")


def downgrade() -> None:
    op.alter_column("subscriptions", "paystack_plan_code",
                     new_column_name="stripe_price_id")

    op.drop_index("ix_subscriptions_paystack_sub_code", table_name="subscriptions")
    op.alter_column("subscriptions", "paystack_sub_code",
                     new_column_name="stripe_subscription_id")
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )

    op.drop_index("ix_organizations_paystack_customer_id", table_name="organizations")
    op.alter_column("organizations", "paystack_customer_id",
                     new_column_name="stripe_customer_id")
    op.create_index(
        "ix_organizations_stripe_customer_id",
        "organizations",
        ["stripe_customer_id"],
        unique=True,
    )
