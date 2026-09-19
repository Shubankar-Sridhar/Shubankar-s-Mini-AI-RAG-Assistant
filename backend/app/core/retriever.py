"""
Hybrid retrieval: dense (vector) + sparse (BM25) + Reciprocal Rank Fusion.
"""
import hashlib
from typing import Any

from app.config import get_settings
from app.core.bm25_index import get_bm25_index
from app.core.embeddings import embed_texts
from app.core.vector_store import VectorStore
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Module-level vector store singleton
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """
    Fuse multiple ranked lists using RRF.

    Args:
        ranked_lists: Each inner list is chunk IDs ordered by relevance.
        k: RRF constant (60 by convention).
        weights: Optional per-list weights. Defaults to equal weights.

    Returns:
        List of (chunk_id, fused_score) sorted descending.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)

    scores: dict[str, float] = {}

    for list_idx, ranked in enumerate(ranked_lists):
        weight = weights[list_idx]
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + rank)

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores


async def hybrid_retrieve(
    query: str,
    top_k: int | None = None,
    vector_weight: float | None = None,
    bm25_weight: float | None = None,
) -> list[dict[str, Any]]:
    """
    Execute hybrid retrieval pipeline.

    1. Embed query
    2. Vector search (dense)
    3. BM25 search (sparse)
    4. RRF fusion
    5. Fetch full chunk data for top results
    """
    top_k = top_k or settings.retrieval_top_k
    vector_weight = vector_weight or settings.retrieval_vector_weight
    bm25_weight = bm25_weight or settings.retrieval_bm25_weight

    store = get_vector_store()
    bm25 = get_bm25_index()

    # Step 1: Embed query
    embeddings = await embed_texts([query])
    query_embedding = embeddings[0]

    # Step 2: Dense retrieval
    vector_results = store.query(query_embedding, n_results=top_k * 3)
    vector_ids = vector_results["ids"][0] if vector_results["ids"] else []

    # Step 3: Sparse retrieval
    bm25_results = bm25.search(query, top_k=top_k * 3)
    bm25_ids = [chunk_id for chunk_id, _ in bm25_results]

    # Step 4: RRF fusion
    fused = reciprocal_rank_fusion(
        ranked_lists=[vector_ids, bm25_ids],
        k=settings.retrieval_rrf_k,
        weights=[vector_weight, bm25_weight],
    )
    top_ids = [chunk_id for chunk_id, _ in fused[:top_k]]

    if not top_ids:
        logger.warning("hybrid_retrieval_empty", extra={"query": query[:100]})
        return []

    # Step 5: Fetch full chunk data
    result = store.collection.get(
        ids=top_ids,
        include=["documents", "metadatas"],
    )

    # Assemble response preserving RRF order
    id_to_idx = {cid: i for i, cid in enumerate(result["ids"])}
    chunks: list[dict[str, Any]] = []
    for chunk_id in top_ids:
        idx = id_to_idx.get(chunk_id)
        if idx is None:
            continue
        chunks.append({
            "id": chunk_id,
            "text": result["documents"][idx],
            "metadata": result["metadatas"][idx],
            "rrf_score": dict(fused)[chunk_id],
        })

    logger.info(
        "hybrid_retrieval_complete",
        extra={
            "query": query[:100],
            "vector_hits": len(vector_ids),
            "bm25_hits": len(bm25_ids),
            "fused_count": len(chunks),
        },
    )
    return chunks


def make_chunk_id(source: str, chunk_index: int) -> str:
    """Deterministic chunk ID from source path and index."""
    raw = f"{source}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]