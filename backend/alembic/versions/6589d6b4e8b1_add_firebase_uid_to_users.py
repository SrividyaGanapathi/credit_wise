"""add firebase uid to users

Revision ID: 6589d6b4e8b1
Revises: 30c2a2716f7c
Create Date: 2026-03-15 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6589d6b4e8b1"
down_revision: Union[str, Sequence[str], None] = "30c2a2716f7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("firebase_uid", sa.String(), nullable=True))
    op.create_index(op.f("ix_users_firebase_uid"), "users", ["firebase_uid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_firebase_uid"), table_name="users")
    op.drop_column("users", "firebase_uid")
