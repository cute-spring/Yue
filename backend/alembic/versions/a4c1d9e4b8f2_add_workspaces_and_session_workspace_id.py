"""add_workspaces_and_session_workspace_id

Revision ID: a4c1d9e4b8f2
Revises: 5c2f0a4d9b31
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4c1d9e4b8f2"
down_revision: Union[str, Sequence[str], None] = "5c2f0a4d9b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_agent_id", sa.String(), nullable=True),
        sa.Column("source_policy_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.String(), nullable=True))
    op.create_index("idx_sessions_workspace_id", "sessions", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_sessions_workspace_id", table_name="sessions")
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("workspace_id")
    op.drop_table("workspaces")
