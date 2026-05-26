"""
Redis client connection management.

Pattern: single client instance created at startup, accessed via dependency injection.
Used for:
- Slack event deduplication (TTL-based)
- KB chunk cache
- APScheduler job store (future)
"""
from collections.abc import AsyncIterable

import redis.asyncio as redis_async

from app.config.settings import settings

#Module-level holder for the client
#Populated at startup, accessed via get_redis() dependency
_redis_client: redis_async.Redis | None = None

async def init_redis() -> redis_async.Redis:
    """
    Create Redis client and verify connection.
    Called from app lifespan at startup.
    """
    global _redis_client
    _redis_client = redis_async.from_url(
        settings.redis_url,
        encoding = "utf-8",
        decode_responses = True,
        #connection pool settings
        max_connections = 10,
        socket_timeout= 5,
        socket_connect_timeout=5,
    )
    await _redis_client.ping()

    return _redis_client

async def close_redis() -> None:
    """
    Close Redis client and connection pool.
    Called from app lifespan at shutdown.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
async def get_redis() -> AsyncIterable[redis_async.Redis]:
    """FastAPI dependency that yields the Redis client.

    Usage in routes:
        @router.post("/something")
        async def handler(redis: Redis = Depends(get_redis)):
            await redis.set("key", "value")
    """
    if _redis_client is None:
        raise RuntimeError(
            "Redis client not initialized. "
            "Check that app lifespan ran init_redis()."
        )

    yield _redis_client
