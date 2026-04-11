"""add_is_active_to_user

Revision ID: e769867dc324
Revises: 98245adc4da6
Create Date: 2026-04-08 20:13:10.825892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # ← add this line

# revision identifiers, used by Alembic.
revision: str = 'e769867dc324'
down_revision: Union[str, Sequence[str], None] = '98245adc4da6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Safe 3-step migration for adding a NOT NULL column to a table that
    already has rows:
      1. Add column as nullable (no error on existing rows)
      2. Backfill all existing rows to TRUE
      3. Alter column to NOT NULL with a permanent server default of TRUE
    """
    # Step 1 — add nullable so PostgreSQL doesn't complain about existing rows
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True))

    # Step 2 — backfill: every existing user is considered active
    op.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")

    # Step 3 — lock in NOT NULL + permanent default for future INSERTs
    op.alter_column(
        'users',
        'is_active',
        nullable=False,
        server_default=sa.true(),   # sa.true() → SQL literal TRUE
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_active')
