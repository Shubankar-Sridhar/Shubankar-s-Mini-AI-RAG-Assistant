"""
Chroma vector store client in HTTP server mode.
"""
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class VectorStore:
    """Wrapper around Chroma HTTP client for chunk storage and retrieval."""

    def __init__(self):
        self.client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection_name = settings.chroma_collection
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunks(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Upsert chunks with embeddings and metadata."""
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(
            "chunks_upserted",
            extra={"count": len(ids), "collection": self.collection_name},
        )

    def get_all(self) -> dict[str, Any]:
        """Retrieve all chunks for BM25 index construction."""
        return self.collection.get(include=["documents", "metadatas"])

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict | None = None,
    ) -> dict[str, Any]:
        """Semantic search over stored chunks."""
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        return self.collection.query(**kwargs)

    def heartbeat(self) -> bool:
        """Health check for Chroma server."""
        try:
            self.client.heartbeat()
            return True
        except Exception as e:
            logger.error("chroma_heartbeat_failed", extra={"error": str(e)})
            return False