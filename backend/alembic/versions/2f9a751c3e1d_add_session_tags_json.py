"""add_session_tags_json

Revision ID: 2f9a751c3e1d
Revises: 9d717f35e292
Create Date: 2026-04-10 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f9a751c3e1d'
down_revision: Union[str, Sequence[str], None] = '9d717f35e292'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_column("tags_json")
