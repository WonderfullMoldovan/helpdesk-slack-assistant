"""
Database engine and session management.

Pattern:
- One AsyncEngine for the entire app (connection pool)
- One AsyncSession per request (via FastAPI dependency)

The engine is created in app lifespan and disposed at shutdown.
Sessions are short-lived — created per request, closed at request end.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import settings

#Module-level holders - populated by init_db() in lifespan
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database() -> None:
    """
    Create the async engine and session factory.
    Called from app lifespan at startup.

    Verifies connectivity by issuing a SELECT 1 — fails fast if DB unreachable.
    """
    global _engine, _session_factory

    if _engine is not None or _session_factory is not None:
        raise RuntimeError("Database already initialized")

    # Create the async engine with connection pooling
    _engine = create_async_engine(
        settings.postgres_dsn,
        # Connection pool settings
        pool_size=10,  # Max number of connections in the pool
        max_overflow=20,  # Max number of connections to create beyond the pool_size
        pool_pre_ping = True,  # Test connections before using them
        pool_recycle=3600,  # Recycle connections after 1 hour
        # echo=True,  # Log SQL queries for debugging (disable in production)
        echo = settings.is_development and settings.log_level == "DEBUG",
    )
    # Create a session maker bound to this engine
    _session_factory = async_sessionmaker(
        bind = _engine, # Use the engine we just created
        expire_on_commit=False, # objects stay usable after commit
        autoflush=False # explicit flush only — clearer transaction boundaries
    )
    # Verify connectivity with a simple query
    from sqlalchemy import text
    async with _engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_database() -> None:
    """
    Dispose the async engine and session factory.
    Called from app lifespan at shutdown.
    """
    global _engine

    if _engine is not None:
        await _engine.dispose()
        _engine = None

async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """
    FastAPI dependency: yields a new AsyncSession per request.

    Session is automatically:
    - Created from session factory
    - Rolled back if handler raises an exception
    - Closed at request end

    Usage:
        @router.post("/something")
        async def handler(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(User).where(...))
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized")

    async with _session_factory() as session:
        try:
            yield session
            # Note: we don't commit here — handlers should manage transactions explicitly.
            # This allows for more complex flows (e.g., multiple commits, rollbacks).
        except Exception:
            # On any exception, rollback uncommitted changes
            await session.rollback()
            raise
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Returns the session factory for use outside of FastAPI request scope
    (e.g., background tasks, scripts).

    Use FastAPI dependency `get_db_session` inside request handlers.
    Use this function in background tasks or standalone scripts.

    Raises:
        RuntimeError: if init_database() has not been called yet.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )
    return _session_factory
