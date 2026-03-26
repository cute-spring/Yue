"""add_embedding_column_for_vector_search

Revision ID: 9d717f35e292
Revises: b0a4fcf5acb3
Create Date: 2026-03-27 07:04:43.831864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d717f35e292'
down_revision: Union[str, Sequence[str], None] = 'b0a4fcf5acb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('embedding', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'embedding')
