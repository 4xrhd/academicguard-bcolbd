"""
session.py — SQLAlchemy async engine and session factory.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

db_url = (
    settings.DATABASE_URL.replace("postgresql+psycopg2", "postgresql+asyncpg")
    if settings.DATABASE_URL
    else "postgresql+asyncpg://academicguard:academicguard@localhost:5432/academicguard"
)

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create tables on startup (dev only — production uses Alembic migrations)."""
    from app.db import models  # noqa: F401 — ensure models are registered
    from sqlalchemy import text
    async with engine.begin() as conn:
        # In production, comment out the line below and rely on Alembic
        await conn.run_sync(Base.metadata.create_all)

        # Apply schema updates for existing tables (idempotent ALTERs)
        await conn.execute(text("""
            ALTER TABLE IF EXISTS risk_scores 
            ADD COLUMN IF NOT EXISTS weight_profile VARCHAR(20) NOT NULL DEFAULT 'code_present';
        """))
        await conn.execute(text("""
            ALTER TABLE IF EXISTS risk_scores 
            ALTER COLUMN code_sim_max DROP NOT NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE IF EXISTS batches 
            ADD COLUMN IF NOT EXISTS total_marks FLOAT NULL,
            ADD COLUMN IF NOT EXISTS marking_config JSONB NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE IF EXISTS submissions 
            ADD COLUMN IF NOT EXISTS marks_obtained FLOAT NULL,
            ADD COLUMN IF NOT EXISTS marks_breakdown JSONB NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE IF EXISTS training_runs 
            ALTER COLUMN user_id DROP NOT NULL;
        """))


from collections.abc import AsyncGenerator
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
