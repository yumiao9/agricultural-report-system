"""Database engine and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings


# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency: yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables and add missing columns."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Try to add new columns that might be missing from old schema
        try:
            from sqlalchemy import text as sa_text
            await conn.execute(sa_text("ALTER TABLE reports ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"))
        except Exception:
            pass  # Column already exists
        try:
            await conn.execute(sa_text("ALTER TABLE reports ADD COLUMN step_data JSON"))
        except Exception:
            pass
        try:
            await conn.execute(sa_text("ALTER TABLE reports ADD COLUMN error_message VARCHAR(500)"))
        except Exception:
            pass


async def close_db():
    """Dispose the engine."""
    await engine.dispose()
