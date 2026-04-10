"""add pdf_store table

Revision ID: a3e7b1d90c52
Revises: d9a1f4c82e3b
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3e7b1d90c52"
down_revision: Union[str, None] = "d9a1f4c82e3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pdf_store",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("pdf_type", sa.String(), nullable=False),
        sa.Column("gcs_path", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("quarter", sa.String(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "downloaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pdf_store_card_id", "pdf_store", ["card_id"])
    op.create_index("ix_pdf_store_pdf_type", "pdf_store", ["pdf_type"])
    op.create_index("ix_pdf_store_is_current", "pdf_store", ["is_current"])
    # Unique index: only one current PDF per (card, type)
    op.create_index(
        "ix_pdf_store_card_type_current",
        "pdf_store",
        ["card_id", "pdf_type", "is_current"],
    )


def downgrade() -> None:
    op.drop_index("ix_pdf_store_card_type_current", table_name="pdf_store")
    op.drop_index("ix_pdf_store_is_current", table_name="pdf_store")
    op.drop_index("ix_pdf_store_pdf_type", table_name="pdf_store")
    op.drop_index("ix_pdf_store_card_id", table_name="pdf_store")
    op.drop_table("pdf_store")
