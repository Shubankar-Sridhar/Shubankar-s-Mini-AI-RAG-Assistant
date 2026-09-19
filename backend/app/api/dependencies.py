"""
Shared FastAPI dependencies.

Currently thin; exists so future auth, rate limiting, and
per-user API key resolution can be injected without refactoring routes.
"""
from typing import AsyncGenerator

from app.core.cache import get_l2
from app.core.retriever import get_vector_store
from app.logging_config import get_logger

logger = get_logger(__name__)


async def ensure_redis() -> AsyncGenerator[None, None]:
    """Lifespan-style hook: ensure Redis is connected for the request."""
    l2 = get_l2()
    if l2.client is None:
        await l2.connect()
    yield


def vector_store_dep():
    return get_vector_store()