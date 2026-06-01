"""add_workspace_sources

Revision ID: c7e9a21b4d6f
Revises: a4c1d9e4b8f2
Create Date: 2026-05-30 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e9a21b4d6f"
down_revision: Union[str, Sequence[str], None] = "a4c1d9e4b8f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_sources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_ref", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ready"),
        sa.Column("source_metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_workspace_sources_workspace_id", "workspace_sources", ["workspace_id"], unique=False)
    op.create_index(
        "idx_workspace_sources_workspace_type",
        "workspace_sources",
        ["workspace_id", "source_type"],
        unique=False,
    )
    op.create_index(
        "idx_workspace_sources_workspace_ref",
        "workspace_sources",
        ["workspace_id", "source_ref"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_workspace_sources_workspace_ref", table_name="workspace_sources")
    op.drop_index("idx_workspace_sources_workspace_type", table_name="workspace_sources")
    op.drop_index("idx_workspace_sources_workspace_id", table_name="workspace_sources")
    op.drop_table("workspace_sources")
