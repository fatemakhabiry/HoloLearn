"""update schedule table with created_by_user_id 

Revision ID: b488133405a7
Revises: 09cd12ac78fe
Create Date: 2026-01-23 21:34:59.921115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b488133405a7'
down_revision: Union[str, Sequence[str], None] = '09cd12ac78fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),

        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.user_id'],
            name='schedules_created_by_user_id_fkey'
        ),
    )



def downgrade() -> None:
    op.drop_table('schedules')
