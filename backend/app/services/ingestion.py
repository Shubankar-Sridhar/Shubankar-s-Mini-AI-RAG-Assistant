"""
Document ingestion: parse PDF → chunk → embed → store → build BM25.
"""
import os
from typing import Any

from app.config import get_settings
from app.core.bm25_index import get_bm25_index
from app.core.chunker import chunk_by_headings
from app.core.embeddings import embed_texts
from app.core.pdf_parser import parse_pdf
from app.core.retriever import make_chunk_id, get_vector_store
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def ingest_pdf(
    pdf_path: str,
    hybrid_parse: bool = False,
    force_ocr: bool = False,
) -> dict[str, Any]:
    """
    Full ingestion pipeline for a single PDF.

    Returns summary with chunk count and parsed output paths.
    """
    logger.info("ingestion_started", extra={"pdf_path": pdf_path})

    # Step 1: Parse
    parsed = parse_pdf(
        pdf_path,
        output_dir=settings.parsed_dir,
        hybrid=hybrid_parse,
        force_ocr=force_ocr,
    )

    # Step 2: Chunk
    chunks = chunk_by_headings(
        markdown=parsed.markdown,
        source_path=pdf_path,
    )

    if not chunks:
        logger.warning("ingestion_no_chunks", extra={"pdf_path": pdf_path})
        return {"status": "empty", "pdf_path": pdf_path, "chunk_count": 0}

    # Step 3: Generate deterministic IDs
    chunk_ids = [
        make_chunk_id(pdf_path, i)
        for i in range(len(chunks))
    ]

    # Step 4: Embed
    texts = [c.text for c in chunks]
    embeddings = await embed_texts(texts)

    # Step 5: Store in Chroma
    store = get_vector_store()
    metadatas = []
    for chunk in chunks:
        meta = dict(chunk.metadata)
        meta["source"] = pdf_path
        metadatas.append(meta)

    store.add_chunks(
        ids=chunk_ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    # Step 6: Rebuild BM25 index from all stored chunks
    all_data = store.get_all()
    if all_data["documents"] and all_data["ids"]:
        bm25 = get_bm25_index()
        bm25.build(all_data["documents"], all_data["ids"])

    logger.info(
        "ingestion_complete",
        extra={
            "pdf_path": pdf_path,
            "chunk_count": len(chunks),
            "image_count": len(parsed.images),
        },
    )

    return {
        "status": "success",
        "pdf_path": pdf_path,
        "chunk_count": len(chunks),
        "image_count": len(parsed.images),
        "markdown_path": os.path.join(settings.parsed_dir, f"{os.path.splitext(os.path.basename(pdf_path))[0]}.md"),
    }