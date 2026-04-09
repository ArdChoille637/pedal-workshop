import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add workshop root to path so we can import api modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from api.models.base import Base
from api.models import *  # noqa: F401, F403 - ensure all models are imported

config = context.config

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
