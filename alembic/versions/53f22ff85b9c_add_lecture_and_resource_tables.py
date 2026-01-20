"""add lecture and resource tables

Revision ID: 53f22ff85b9c
Revises: 
Create Date: 2026-01-19 18:46:14.945789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '53f22ff85b9c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create lectures table first
    op.create_table('lectures',
        sa.Column('lecture_id', sa.Integer(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('course_code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('lecture_type', sa.Enum('PREPARED', 'GENERATED', name='lecturetype'), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'GENERATING', 'COMPLETED', 'FAILED', name='lecturestatus'), nullable=False),
        sa.Column('final_content', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(['course_code'], ['courses.course_code'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.user_id'], ),
        sa.PrimaryKeyConstraint('lecture_id')
    )
    
    # Create resources table
    op.create_table('resources',
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('lecture_id', sa.Integer(), nullable=False),
        sa.Column('resource_type', sa.Enum('PDF', 'PPTX', 'VIDEO', 'DOCUMENT', 'OTHER', name='resourcetype'), nullable=False),
        sa.Column('file_path', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['lecture_id'], ['lectures.lecture_id'], ),
        sa.PrimaryKeyConstraint('resource_id')
    )
    
    # FIX: Set any existing invalid lecture_id values to NULL before adding constraint
    op.execute("""
        UPDATE schedules 
        SET lecture_id = NULL 
        WHERE lecture_id IS NOT NULL 
        AND lecture_id NOT IN (SELECT lecture_id FROM lectures)
    """)
    
    # Now add the foreign key constraint
    op.create_foreign_key('fk_schedules_lecture_id', 'schedules', 'lectures', ['lecture_id'], ['lecture_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_schedules_lecture_id', 'schedules', type_='foreignkey')
    op.drop_table('resources')
    op.drop_table('lectures')