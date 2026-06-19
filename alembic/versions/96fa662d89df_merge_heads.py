"""merge_heads

Revision ID: 96fa662d89df
Revises: 59eb9066fdb1, ea84606aaf35
Create Date: 2026-05-27 14:36:00.201860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96fa662d89df'
down_revision: Union[str, Sequence[str], None] = ('59eb9066fdb1', 'ea84606aaf35')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
