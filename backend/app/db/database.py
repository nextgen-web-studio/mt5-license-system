import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

# Ensure we load from infinity_trader/.env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
load_dotenv(env_path)

import re

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

# Auto-convert Supabase POOLER url → DIRECT connection url to completely bypass PgBouncer
# Pooler: postgres.PROJECT_ID:PASS@aws-0-REGION.pooler.supabase.com:PORT/postgres
# Direct: postgres:PASS@db.PROJECT_ID.supabase.co:5432/postgres
if "pooler.supabase.com" in DATABASE_URL:
    match = re.search(r'postgres\.([a-z0-9]+):', DATABASE_URL)
    if match:
        project_id = match.group(1)
        DATABASE_URL = re.sub(r'postgres\.[^:@]+:', 'postgres:', DATABASE_URL)
        DATABASE_URL = re.sub(r'@[^@]+\.pooler\.supabase\.com:\d+/', f'@db.{project_id}.supabase.co:5432/', DATABASE_URL)

DATABASE_URL = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")
DATABASE_URL = DATABASE_URL.replace("?prepared_statement_cache_size=0", "").replace("&prepared_statement_cache_size=0", "")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
