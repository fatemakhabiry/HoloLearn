"""add_description_optional_teacher_to_course

Revision ID: a1b2c3d4e5f6
Revises: e769867dc324
Create Date: 2026-04-09 00:00:00.000000

Changes:
  - courses.description  → new nullable TEXT column
  - courses.teacher_id   → make nullable (allows "Remove Assignment")
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e769867dc324'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add description column (nullable, no backfill needed)
    op.add_column(
        'courses',
        sa.Column('description', sa.String(length=500), nullable=True)
    )

    # 2. Make teacher_id nullable so "Remove Assignment" can set it to NULL.
    #    Drop the existing NOT NULL constraint and keep the FK.
    op.alter_column(
        'courses',
        'teacher_id',
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Restore teacher_id as NOT NULL (set any NULLs to 0 first to avoid errors)
    op.execute("UPDATE courses SET teacher_id = 0 WHERE teacher_id IS NULL")
    op.alter_column(
        'courses',
        'teacher_id',
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_column('courses', 'description')
