"""
BM25 keyword index built from Chroma chunks.
"""
import pickle
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

INDEX_DIR = Path("./data/bm25")
INDEX_DIR.mkdir(parents=True, exist_ok=True)
CORPUS_PATH = INDEX_DIR / "corpus_tokens.pkl"
IDS_PATH = INDEX_DIR / "chunk_ids.pkl"


def tokenize(text: str) -> list[str]:
    """Deterministic tokenizer: lowercase, split on non-alphanumeric runs."""
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


class BM25Index:
    """In-memory BM25 index persisted to disk for fast reload."""

    def __init__(self):
        self.bm25: BM25Okapi | None = None
        self.chunk_ids: list[str] = []
        self.corpus_tokens: list[list[str]] = []

    def build(self, documents: list[str], ids: list[str]) -> None:
        """Build BM25 index from documents and their chunk IDs."""
        self.corpus_tokens = [tokenize(doc) for doc in documents]
        self.chunk_ids = list(ids)
        self.bm25 = BM25Okapi(self.corpus_tokens)

        self._persist()

        logger.info(
            "bm25_index_built",
            extra={"chunk_count": len(self.chunk_ids)},
        )

    def _persist(self) -> None:
        """Save index to disk for fast reload on restart."""
        with open(CORPUS_PATH, "wb") as f:
            pickle.dump(self.corpus_tokens, f)
        with open(IDS_PATH, "wb") as f:
            pickle.dump(self.chunk_ids, f)

    def load(self) -> bool:
        """Load persisted index. Returns True if successful."""
        if not CORPUS_PATH.exists() or not IDS_PATH.exists():
            return False

        with open(CORPUS_PATH, "rb") as f:
            self.corpus_tokens = pickle.load(f)
        with open(IDS_PATH, "rb") as f:
            self.chunk_ids = pickle.load(f)

        self.bm25 = BM25Okapi(self.corpus_tokens)
        logger.info("bm25_index_loaded", extra={"chunk_count": len(self.chunk_ids)})
        return True

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Return (chunk_id, bm25_score) sorted descending."""
        if not self.bm25 or not self.chunk_ids:
            return []

        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        scored = list(zip(self.chunk_ids, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def is_ready(self) -> bool:
        return self.bm25 is not None and len(self.chunk_ids) > 0


# Module-level singleton
_bm25_instance: BM25Index | None = None


def get_bm25_index() -> BM25Index:
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Index()
        _bm25_instance.load()
    return _bm25_instance