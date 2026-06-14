"""add_memory_scope_and_lifecycle_fields

Revision ID: d4b8e2f1c6a7
Revises: 9a7e1c4d5b21
Create Date: 2026-06-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4b8e2f1c6a7"
down_revision: Union[str, Sequence[str], None] = "9a7e1c4d5b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspace_memory_cards",
        sa.Column("scope_type", sa.String(), nullable=False, server_default="workspace"),
    )
    op.add_column(
        "workspace_memory_cards",
        sa.Column("scope_ref", sa.String(), nullable=True),
    )
    op.add_column(
        "workspace_memory_cards",
        sa.Column("why_saved", sa.Text(), nullable=True),
    )
    op.add_column(
        "workspace_memory_cards",
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "workspace_memory_cards",
        sa.Column("editable", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "workspace_memory_cards",
        sa.Column("revocable", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "workspace_memory_cards",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_workspace_memory_cards_scope",
        "workspace_memory_cards",
        ["scope_type", "scope_ref", "status"],
        unique=False,
    )
    op.execute(
        "UPDATE workspace_memory_cards "
        "SET scope_ref = workspace_id "
        "WHERE scope_type IN ('workspace', 'project') AND (scope_ref IS NULL OR TRIM(scope_ref) = '')"
    )

    op.add_column(
        "workspace_memory_candidates",
        sa.Column("scope_type", sa.String(), nullable=False, server_default="workspace"),
    )
    op.add_column(
        "workspace_memory_candidates",
        sa.Column("scope_ref", sa.String(), nullable=True),
    )
    op.add_column(
        "workspace_memory_candidates",
        sa.Column("why_saved", sa.Text(), nullable=True),
    )
    op.add_column(
        "workspace_memory_candidates",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_workspace_memory_candidates_scope",
        "workspace_memory_candidates",
        ["scope_type", "scope_ref", "status"],
        unique=False,
    )
    op.execute(
        "UPDATE workspace_memory_candidates "
        "SET scope_ref = workspace_id "
        "WHERE scope_type IN ('workspace', 'project') AND (scope_ref IS NULL OR TRIM(scope_ref) = '')"
    )


def downgrade() -> None:
    op.drop_index("idx_workspace_memory_candidates_scope", table_name="workspace_memory_candidates")
    op.drop_column("workspace_memory_candidates", "expires_at")
    op.drop_column("workspace_memory_candidates", "why_saved")
    op.drop_column("workspace_memory_candidates", "scope_ref")
    op.drop_column("workspace_memory_candidates", "scope_type")

    op.drop_index("idx_workspace_memory_cards_scope", table_name="workspace_memory_cards")
    op.drop_column("workspace_memory_cards", "expires_at")
    op.drop_column("workspace_memory_cards", "revocable")
    op.drop_column("workspace_memory_cards", "editable")
    op.drop_column("workspace_memory_cards", "pinned")
    op.drop_column("workspace_memory_cards", "why_saved")
    op.drop_column("workspace_memory_cards", "scope_ref")
    op.drop_column("workspace_memory_cards", "scope_type")
