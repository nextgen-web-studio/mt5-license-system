import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

# Add the app directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import Base
from app.models import *

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

def do_run_migrations(connection):
    context.configure(
        connection=connection, target_metadata=target_metadata, compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    
    For Supabase PgBouncer compatibility:
    - Alembic uses DIRECT_URL (port 5432, session pooler) which supports prepared statements
    - If DIRECT_URL not set, falls back to DATABASE_URL with port 6543->5432 swap
    - The main app uses DATABASE_URL (port 6543, transaction pooler) for fast queries
    """
    # Prefer DIRECT_URL for migrations (avoids PgBouncer prepared statement issues)
    database_url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    
    # If still using transaction pooler port 6543, swap to session pooler port 5432
    database_url = database_url.replace(":6543/", ":5432/")
    
    # Strip pgbouncer param if present - not needed with session pooler
    database_url = database_url.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
    database_url = database_url.replace("?prepared_statement_cache_size=0", "").replace("&prepared_statement_cache_size=0", "")
    
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
