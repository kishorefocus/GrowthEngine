"""
Redis-based rate limiter for public endpoints.
Uses a sliding window counter in Redis.
"""
import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from app.core.config import settings

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def rate_limit(
    request: Request,
    max_requests: int = 60,
    window_seconds: int = 60,
    key_prefix: str = "rl",
) -> None:
    """
    Sliding-window rate limiter. Call as a FastAPI dependency.
    Raises HTTP 429 if the limit is exceeded.

    Usage:
        @app.get("/endpoint")
        async def endpoint(_: None = Depends(rate_limit)):
            ...
    """
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    redis_key = f"{key_prefix}:{client_ip}:{path}"

    try:
        r = get_redis()
        now = int(time.time())
        window_start = now - window_seconds

        pipe = r.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds)
        results = await pipe.execute()

        count = results[2]
        if count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
                headers={"Retry-After": str(window_seconds)},
            )
    except HTTPException:
        raise
    except Exception:
        # If Redis is unavailable, fail open (don't block requests)
        pass


def make_rate_limiter(max_requests: int = 60, window_seconds: int = 60):
    """Factory that returns a rate limiter with custom limits."""
    async def limiter(request: Request) -> None:
        await rate_limit(request, max_requests=max_requests, window_seconds=window_seconds)
    return limiter
