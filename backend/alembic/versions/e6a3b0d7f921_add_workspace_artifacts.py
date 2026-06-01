"""add_workspace_artifacts

Revision ID: e6a3b0d7f921
Revises: c7e9a21b4d6f
Create Date: 2026-05-30 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6a3b0d7f921"
down_revision: Union[str, Sequence[str], None] = "c7e9a21b4d6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_session_id", sa.String(), nullable=True),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("action_state_id", sa.Integer(), nullable=True),
        sa.Column("artifact_path", sa.String(), nullable=True),
        sa.Column("content_ref", sa.String(), nullable=True),
        sa.Column("artifact_metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["action_state_id"], ["action_states.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_workspace_artifacts_workspace_id", "workspace_artifacts", ["workspace_id"], unique=False)
    op.create_index(
        "idx_workspace_artifacts_workspace_type",
        "workspace_artifacts",
        ["workspace_id", "artifact_type"],
        unique=False,
    )
    op.create_index(
        "idx_workspace_artifacts_workspace_path",
        "workspace_artifacts",
        ["workspace_id", "artifact_path"],
        unique=False,
    )
    op.create_index(
        "idx_workspace_artifacts_workspace_action_state",
        "workspace_artifacts",
        ["workspace_id", "action_state_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_workspace_artifacts_workspace_action_state", table_name="workspace_artifacts")
    op.drop_index("idx_workspace_artifacts_workspace_path", table_name="workspace_artifacts")
    op.drop_index("idx_workspace_artifacts_workspace_type", table_name="workspace_artifacts")
    op.drop_index("idx_workspace_artifacts_workspace_id", table_name="workspace_artifacts")
    op.drop_table("workspace_artifacts")
