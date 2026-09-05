"""add_message_chart_artifacts_json

Revision ID: f2b4d6c8a901
Revises: e6a3b0d7f921
Create Date: 2026-07-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2b4d6c8a901"
down_revision: Union[str, Sequence[str], None] = "e6a3b0d7f921"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chart_artifacts_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("chart_artifacts_json")
