"""add_message_attachments_column

Revision ID: 6b3e1f7a9c4d
Revises: 2f9a751c3e1d
Create Date: 2026-04-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b3e1f7a9c4d"
down_revision: Union[str, Sequence[str], None] = "2f9a751c3e1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("attachments", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_column("attachments")
