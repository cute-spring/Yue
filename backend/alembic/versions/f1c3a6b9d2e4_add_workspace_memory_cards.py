"""add_workspace_memory_cards

Revision ID: f1c3a6b9d2e4
Revises: e6a3b0d7f921
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1c3a6b9d2e4"
down_revision: Union[str, Sequence[str], None] = "e6a3b0d7f921"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_memory_cards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("source_session_id", sa.String(), nullable=True),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("memory_metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_workspace_memory_cards_workspace_id",
        "workspace_memory_cards",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "idx_workspace_memory_cards_workspace_type_status",
        "workspace_memory_cards",
        ["workspace_id", "memory_type", "status"],
        unique=False,
    )
    op.create_index(
        "idx_workspace_memory_cards_workspace_last_used",
        "workspace_memory_cards",
        ["workspace_id", "last_used_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_workspace_memory_cards_workspace_last_used", table_name="workspace_memory_cards")
    op.drop_index("idx_workspace_memory_cards_workspace_type_status", table_name="workspace_memory_cards")
    op.drop_index("idx_workspace_memory_cards_workspace_id", table_name="workspace_memory_cards")
    op.drop_table("workspace_memory_cards")
