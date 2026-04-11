from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sqlmodel  # ← add this once, prevents NameError in all future migrations
# Import your SQLModel metadata and engine
from app.core.database import engine  # Your database engine
from sqlmodel import SQLModel

# Import ALL your models so Alembic can detect them
from app.models.user import User
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.schedule import Schedule
from app.models.lecture import Lecture  # NEW
from app.models.resource import Resource  # NEW
from app.models.lecture_pipeline import LecturePipeline
# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the metadata for autogenerate support
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # Use your existing engine instead of creating a new one
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()