"""add spend tracker

Revision ID: 30c2a2716f7c
Revises: 553a5f31132d
Create Date: 2026-03-08 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "30c2a2716f7c"
down_revision: Union[str, Sequence[str], None] = "553a5f31132d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "spend_tracker",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("spent_amount", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["rule_id"], ["reward_rules.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "rule_id",
            "period_start",
            name="uq_spend_tracker_user_rule_period",
        ),
    )
    op.create_index(op.f("ix_spend_tracker_period_start"), "spend_tracker", ["period_start"], unique=False)
    op.create_index(op.f("ix_spend_tracker_rule_id"), "spend_tracker", ["rule_id"], unique=False)
    op.create_index(op.f("ix_spend_tracker_user_id"), "spend_tracker", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_spend_tracker_user_id"), table_name="spend_tracker")
    op.drop_index(op.f("ix_spend_tracker_rule_id"), table_name="spend_tracker")
    op.drop_index(op.f("ix_spend_tracker_period_start"), table_name="spend_tracker")
    op.drop_table("spend_tracker")
