"""add_message_continuation_fields

Revision ID: 5c2f0a4d9b31
Revises: 6b3e1f7a9c4d
Create Date: 2026-05-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5c2f0a4d9b31"
down_revision: Union[str, Sequence[str], None] = "6b3e1f7a9c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("continuation_of", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("continuation_root_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("continuation_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("content_type", sa.String(), nullable=True))
    op.create_index(
        "idx_messages_continuation_root",
        "messages",
        ["continuation_root_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_messages_continuation_root", table_name="messages")
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("content_type")
        batch_op.drop_column("continuation_status")
        batch_op.drop_column("continuation_root_id")
        batch_op.drop_column("continuation_of")
