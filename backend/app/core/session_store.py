"""
Redis-backed conversation session storage.

Each session is a Redis List of JSON-encoded ChatMessage dicts.
TTL is applied on every write so active sessions stay alive.
"""
import json
import uuid
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SessionStore:
    """Redis List-backed conversation history."""

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
                logger.info("session_store_connected")
            except Exception as e:
                logger.error("session_store_connect_failed", extra={"error": str(e)})
                self.client = None

    @staticmethod
    def _key(session_id: str) -> str:
        return f"session:{session_id}:messages"

    @staticmethod
    def new_session_id() -> str:
        return uuid.uuid4().hex

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a message to the session and refresh TTL."""
        if not self.client:
            await self.connect()
        if not self.client:
            logger.warning("session_append_skipped_no_redis")
            return

        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        key = self._key(session_id)
        await self.client.rpush(key, json.dumps(msg))
        await self.client.expire(key, settings.redis_session_ttl)

    async def get_messages(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch messages. If limit is given, returns the last `limit` messages.
        """
        if not self.client:
            await self.connect()
        if not self.client:
            return []

        key = self._key(session_id)
        if limit is None:
            raw = await self.client.lrange(key, 0, -1)
        else:
            raw = await self.client.lrange(key, -limit, -1)

        messages: list[dict[str, Any]] = []
        for item in raw:
            try:
                messages.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        return messages

    async def count(self, session_id: str) -> int:
        if not self.client:
            await self.connect()
        if not self.client:
            return 0
        return await self.client.llen(self._key(session_id))

    async def delete(self, session_id: str) -> None:
        if not self.client:
            await self.connect()
        if not self.client:
            return
        await self.client.delete(self._key(session_id))

    async def exists(self, session_id: str) -> bool:
        return await self.count(session_id) > 0


_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store