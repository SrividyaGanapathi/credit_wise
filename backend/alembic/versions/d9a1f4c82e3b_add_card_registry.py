"""add card_registry table

Revision ID: d9a1f4c82e3b
Revises: cf0ffde4979e
Create Date: 2026-04-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9a1f4c82e3b"
down_revision: Union[str, None] = "cf0ffde4979e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "card_registry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("issuer", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("network", sa.String(), nullable=True),
        sa.Column("card_type", sa.String(), nullable=False, server_default="personal"),
        sa.Column("annual_fee_usd", sa.Integer(), nullable=True),
        sa.Column("product_url", sa.Text(), nullable=True),
        sa.Column("benefits_pdf_url", sa.Text(), nullable=True),
        sa.Column("terms_pdf_url", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_registry_slug", "card_registry", ["slug"], unique=True)
    op.create_index("ix_card_registry_issuer", "card_registry", ["issuer"])
    op.create_index("ix_card_registry_source", "card_registry", ["source"])
    op.create_index("ix_card_registry_is_active", "card_registry", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_card_registry_is_active", table_name="card_registry")
    op.drop_index("ix_card_registry_source", table_name="card_registry")
    op.drop_index("ix_card_registry_issuer", table_name="card_registry")
    op.drop_index("ix_card_registry_slug", table_name="card_registry")
    op.drop_table("card_registry")
