"""
Redis service module.
Wraps the redis-py async client with connection management and health check.
"""
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level client (initialised in lifespan)
_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis:
    """Return (or lazily create) the shared Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection on shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


async def check_redis_connection() -> bool:
    """Ping Redis; return True if reachable."""
    try:
        client = await get_redis_client()
        response = await client.ping()
        return response is True
    except Exception as exc:
        logger.error("Redis connection failed: %s", exc)
        return False
