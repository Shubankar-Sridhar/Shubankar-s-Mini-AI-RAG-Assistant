"""
Three-tier cache: L1 in-memory LRU, L2 Redis, L3 semantic (embedding-based).
"""
import hashlib
import json
from collections import OrderedDict
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def make_cache_key(payload: dict[str, Any]) -> str:
    """Deterministic key from normalized payload."""
    normalized = json.dumps(payload, sort_keys=True, default=str).lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


class L1Cache:
    """In-process LRU with TTL, capped by entry count."""

    def __init__(self, max_size: int, ttl: int):
        self.max_size = max_size
        self.ttl = ttl
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        import time
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        import time
        if key in self._store:
            self._store.pop(key)
        elif len(self._store) >= self.max_size:
            self._store.popitem(last=False)
        self._store[key] = (value, time.time() + self.ttl)


class L2Cache:
    """Redis-backed distributed cache."""

    def __init__(self):
        self.client: aioredis.Redis | None = None

    async def connect(self) -> None:
        if self.client is None:
            self.client = aioredis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
            )
            try:
                await self.client.ping()
                logger.info("redis_connected")
            except Exception as e:
                logger.error("redis_connect_failed", extra={"error": str(e)})
                self.client = None

    async def get(self, key: str) -> Any | None:
        if not self.client:
            return None
        raw = await self.client.get(f"cache:{key}")
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self.client:
            return
        ttl = ttl or settings.l2_cache_ttl
        await self.client.set(f"cache:{key}", json.dumps(value, default=str), ex=ttl)


_l1: L1Cache | None = None
_l2: L2Cache | None = None


def get_l1() -> L1Cache:
    global _l1
    if _l1 is None:
        _l1 = L1Cache(settings.l1_cache_max_size, settings.l1_cache_ttl)
    return _l1


def get_l2() -> L2Cache:
    global _l2
    if _l2 is None:
        _l2 = L2Cache()
    return _l2


async def cache_get(key: str) -> Any | None:
    val = get_l1().get(key)
    if val is not None:
        logger.debug("cache_hit_l1", extra={"key": key[:16]})
        return val
    val = await get_l2().get(key)
    if val is not None:
        logger.debug("cache_hit_l2", extra={"key": key[:16]})
        get_l1().set(key, val)
        return val
    return None


async def cache_set(key: str, value: Any) -> None:
    get_l1().set(key, value)
    await get_l2().set(key, value)