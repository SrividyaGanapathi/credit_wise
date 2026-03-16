"""add recommendation events

Revision ID: cf0ffde4979e
Revises: 6589d6b4e8b1
Create Date: 2026-03-15 16:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cf0ffde4979e"
down_revision: Union[str, None] = "6589d6b4e8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendation_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("auth_mode", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("recommended_card_ids", sa.JSON(), nullable=False),
        sa.Column("selected_card_id", sa.Integer(), nullable=True),
        sa.Column("selected_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["selected_card_id"], ["cards.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_events_auth_mode"), "recommendation_events", ["auth_mode"], unique=False)
    op.create_index(op.f("ix_recommendation_events_category"), "recommendation_events", ["category"], unique=False)
    op.create_index(op.f("ix_recommendation_events_channel"), "recommendation_events", ["channel"], unique=False)
    op.create_index(op.f("ix_recommendation_events_country"), "recommendation_events", ["country"], unique=False)
    op.create_index(op.f("ix_recommendation_events_created_at"), "recommendation_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_recommendation_events_event_type"), "recommendation_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_recommendation_events_request_id"), "recommendation_events", ["request_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_selected_card_id"), "recommendation_events", ["selected_card_id"], unique=False)
    op.create_index(op.f("ix_recommendation_events_user_id"), "recommendation_events", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recommendation_events_user_id"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_selected_card_id"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_request_id"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_event_type"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_created_at"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_country"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_channel"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_category"), table_name="recommendation_events")
    op.drop_index(op.f("ix_recommendation_events_auth_mode"), table_name="recommendation_events")
    op.drop_table("recommendation_events")
