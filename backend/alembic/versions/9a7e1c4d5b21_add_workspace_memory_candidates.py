"""add_workspace_memory_candidates

Revision ID: 9a7e1c4d5b21
Revises: f1c3a6b9d2e4
Create Date: 2026-06-03 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a7e1c4d5b21"
down_revision: Union[str, Sequence[str], None] = "f1c3a6b9d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspace_memory_cards",
        sa.Column("supersedes_memory_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workspace_memory_cards_supersedes_memory_id",
        "workspace_memory_cards",
        "workspace_memory_cards",
        ["supersedes_memory_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_workspace_memory_cards_workspace_supersedes",
        "workspace_memory_cards",
        ["workspace_id", "supersedes_memory_id"],
        unique=False,
    )

    op.create_table(
        "workspace_memory_candidates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("suggested_action", sa.String(), nullable=True),
        sa.Column("conflict_memory_id", sa.String(), nullable=True),
        sa.Column("source_session_id", sa.String(), nullable=True),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("candidate_metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conflict_memory_id"], ["workspace_memory_cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_workspace_memory_candidates_workspace_id",
        "workspace_memory_candidates",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "idx_workspace_memory_candidates_workspace_status",
        "workspace_memory_candidates",
        ["workspace_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_workspace_memory_candidates_workspace_conflict",
        "workspace_memory_candidates",
        ["workspace_id", "conflict_memory_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_workspace_memory_candidates_workspace_conflict", table_name="workspace_memory_candidates")
    op.drop_index("idx_workspace_memory_candidates_workspace_status", table_name="workspace_memory_candidates")
    op.drop_index("idx_workspace_memory_candidates_workspace_id", table_name="workspace_memory_candidates")
    op.drop_table("workspace_memory_candidates")

    op.drop_index("idx_workspace_memory_cards_workspace_supersedes", table_name="workspace_memory_cards")
    op.drop_constraint("fk_workspace_memory_cards_supersedes_memory_id", "workspace_memory_cards", type_="foreignkey")
    op.drop_column("workspace_memory_cards", "supersedes_memory_id")
