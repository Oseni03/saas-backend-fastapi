"""
Redis client — used for caching, rate limiting, and future task queues.
"""

from functools import lru_cache

import redis.asyncio as aioredis

from app.config import settings


@lru_cache
def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    return aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )


async def set_with_ttl(key: str, value: str, ttl_seconds: int) -> None:
    r = get_redis()
    await r.set(key, value, ex=ttl_seconds)


async def get_value(key: str) -> str | None:
    r = get_redis()
    return await r.get(key)


async def delete_key(key: str) -> None:
    r = get_redis()
    await r.delete(key)


async def key_exists(key: str) -> bool:
    r = get_redis()
    return bool(await r.exists(key))
