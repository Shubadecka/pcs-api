"""Database connection management using SQLAlchemy async."""

from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from pgvector.asyncpg import register_vector

from app.core.config import settings


# Create async engine
# Using asyncpg as the driver
_engine = create_async_engine(
    f"postgresql+asyncpg://{settings.database_user}:{settings.database_password}@{settings.database_host}:{settings.database_port}/{settings.database_name}",
    echo=False,  # Set to True for SQL query logging
    poolclass=NullPool,  # Use NullPool for better async compatibility
)


@event.listens_for(_engine.sync_engine, "connect")
def _register_vector_codec(dbapi_conn, _connection_record):
    dbapi_conn.run_async(register_vector)


# Create async session factory
_async_session_factory = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def create_db_session() -> AsyncSession:
    """Create a standalone database session for use outside of request context.

    Returns an AsyncSession that acts as an async context manager, suitable
    for background tasks that outlive the originating HTTP request.

    Usage::

        async with create_db_session() as db:
            ...
    """
    return _async_session_factory()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    
    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize the database (create tables if needed)."""
    from app.core.models import metadata

    async with _engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await _engine.dispose()


# Legacy aliases for compatibility
async def init_db_pool() -> None:
    """Initialize database - alias for init_db."""
    await init_db()


async def close_db_pool() -> None:
    """Close database - alias for close_db."""
    await close_db()
