"""add_lecture_pipelines_table

Revision ID: 98245adc4da6
Revises: 43fad2e23673
Create Date: 2026-04-08 02:25:46.479540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '98245adc4da6'
down_revision: Union[str, Sequence[str], None] = '43fad2e23673'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Safely create the ENUM type (ignore if already exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE pipelinestatus AS ENUM ('QUEUED', 'GENERATING', 'COMPLETED', 'FAILED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Step 2: Create table only if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS lecture_pipelines (
            lecture_id INTEGER NOT NULL,
            status pipelinestatus NOT NULL,
            script_path VARCHAR,
            num_steps INTEGER NOT NULL,
            audio_cfg FLOAT NOT NULL,
            text_cfg FLOAT NOT NULL,
            seed INTEGER NOT NULL,
            preset VARCHAR NOT NULL,
            avatar_backend VARCHAR NOT NULL,
            output_video_path VARCHAR,
            error_message VARCHAR,
            created_at TIMESTAMP NOT NULL,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            PRIMARY KEY (lecture_id),
            FOREIGN KEY (lecture_id) REFERENCES lectures(lecture_id)
        )
    """)

    # Step 3: Drop columns from lectures (safe version)
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS avatar_backend")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS seed")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS started_at")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS script_path")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS completed_at")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS output_video_path")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS audio_cfg")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS preset")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS text_cfg")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS error_message")
    op.execute("ALTER TABLE lectures DROP COLUMN IF EXISTS num_steps")


def downgrade() -> None:
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS num_steps INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS error_message VARCHAR")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS text_cfg FLOAT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS preset VARCHAR NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS audio_cfg FLOAT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS output_video_path VARCHAR")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS script_path VARCHAR")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS started_at TIMESTAMP")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS seed INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE lectures ADD COLUMN IF NOT EXISTS avatar_backend VARCHAR NOT NULL DEFAULT ''")
    op.execute("DROP TABLE IF EXISTS lecture_pipelines")
    op.execute("DROP TYPE IF EXISTS pipelinestatus")