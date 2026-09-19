"""
Local embedding generation via Ollama (default) or OpenAI (fallback).
"""
from typing import Any

import httpx
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.

    Uses Ollama's /api/embed endpoint (L2-normalized vectors).
    """
    if settings.embedding_provider == "local":
        return await _embed_ollama(texts)
    elif settings.embedding_provider == "openai":
        return await _embed_openai(texts)
    else:
        raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")


async def _embed_ollama(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via local Ollama instance."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={
                    "model": settings.embedding_model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            logger.info(
                "embeddings_generated",
                extra={"provider": "ollama", "count": len(embeddings)},
            )
            return embeddings
        except httpx.HTTPError as e:
            logger.error("embedding_failed", extra={"provider": "ollama", "error": str(e)})
            raise


async def _embed_openai(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via OpenAI API."""
    api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set for OpenAI embeddings")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "text-embedding-3-small",
                "input": texts,
            },
        )
        response.raise_for_status()
        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        logger.info(
            "embeddings_generated",
            extra={"provider": "openai", "count": len(embeddings)},
        )
        return embeddings