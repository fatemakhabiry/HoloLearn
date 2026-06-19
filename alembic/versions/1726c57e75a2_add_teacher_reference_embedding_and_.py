"""add teacher reference_embedding and identity_verifications table

Revision ID: 1726c57e75a2
Revises: 5d72c48fdc2b
Create Date: 2026-06-17 22:38:47.210109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1726c57e75a2'
down_revision: Union[str, Sequence[str], None] = '5d72c48fdc2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('identity_verifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('teacher_id', sa.Integer(), nullable=False),
    sa.Column('lecture_id', sa.Integer(), nullable=False),
    sa.Column('distance', sa.Float(), nullable=False),
    sa.Column('passed', sa.Boolean(), nullable=False),
    sa.Column('captured_image_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['lecture_id'], ['lectures.lecture_id'], ),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.user_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_identity_verifications_created_at'), 'identity_verifications', ['created_at'], unique=False)
    op.create_index(op.f('ix_identity_verifications_lecture_id'), 'identity_verifications', ['lecture_id'], unique=False)
    op.create_index(op.f('ix_identity_verifications_teacher_id'), 'identity_verifications', ['teacher_id'], unique=False)
    op.add_column('teachers', sa.Column('reference_embedding', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    # NOTE: the checkpoints / checkpoint_writes / checkpoint_blobs /
    # checkpoint_migrations drop_table calls that autogenerate produced
    # here have been REMOVED. Those tables belong to LangGraph's
    # PostgreSQL checkpointer, not SQLModel's metadata — autogenerate
    # sees them as "extra" tables and wants to drop them. Never let that
    # happen; see the include_object reminder below.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('teachers', 'reference_embedding')
    op.drop_index(op.f('ix_identity_verifications_teacher_id'), table_name='identity_verifications')
    op.drop_index(op.f('ix_identity_verifications_lecture_id'), table_name='identity_verifications')
    op.drop_index(op.f('ix_identity_verifications_created_at'), table_name='identity_verifications')
    op.drop_table('identity_verifications')
    # The checkpoint_* table recreation blocks have been removed too —
    # those tables were never dropped in upgrade(), so there's nothing
    # to recreate here.