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
    Uses Supabase direct connection (bypasses PgBouncer entirely) for full
    prepared statement support during migrations.
    """
    import re
    database_url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

    # Auto-convert Supabase POOLER url → DIRECT connection url
    # Pooler: postgres.PROJECT_ID:PASS@aws-0-REGION.pooler.supabase.com:PORT/postgres
    # Direct: postgres:PASS@db.PROJECT_ID.supabase.co:5432/postgres
    if "pooler.supabase.com" in database_url:
        match = re.search(r'postgres\.([a-z0-9]+):', database_url)
        if match:
            project_id = match.group(1)
            # Replace username: postgres.PROJECT_ID -> postgres
            database_url = re.sub(r'postgres\.[^:@]+:', 'postgres:', database_url)
            # Replace host+port: @*.pooler.supabase.com:PORT/ -> @db.PROJECT_ID.supabase.co:5432/
            database_url = re.sub(r'@[^@]+\.pooler\.supabase\.com:\d+/', f'@db.{project_id}.supabase.co:5432/', database_url)

    # Strip pgbouncer params - not needed with direct connection
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
