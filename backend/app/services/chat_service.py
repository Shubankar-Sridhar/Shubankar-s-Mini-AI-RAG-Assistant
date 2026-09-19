"""
Chat orchestration: context assembly → retrieval → LLM streaming.

Session history is loaded via context_manager, retrieval injects
document context, and the final prompt is streamed to the LLM.
"""
import json
from typing import Any, AsyncGenerator

from app.config import get_settings
from app.core.llm_client import resolve_provider, UniversalLLMClient
from app.core.retriever import hybrid_retrieve
from app.core.session_store import get_session_store
from app.logging_config import get_logger
from app.services.context_manager import build_context_messages

logger = get_logger(__name__)
settings = get_settings()

def sse(event: str, data: Any) -> dict[str, str]:
    """Build an SSE-ready dict with JSON-encoded data."""
    return {"event": event, "data": json.dumps(data)}

SYSTEM_PROMPT = (
    "You are a knowledge assistant. Answer the user's question using ONLY "
    "the provided document context and prior conversation. If the context "
    "does not contain the answer, say you cannot find it in the uploaded "
    "documents. Cite sources as [1], [2] matching the numbered context blocks."
)


def build_context_block(chunks: list[dict[str, Any]]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk["metadata"].get("source", "unknown")
        heading = chunk["metadata"].get("heading", "")
        header = f"[{i}] {source}"
        if heading:
            header += f" — {heading}"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


async def stream_chat_response(
    query: str,
    session_id: str,
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.2,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Yield SSE-ready event dicts: status → sources → tokens → done.
    Persists both user and assistant messages to the session.
    """
    store = get_session_store()

    # Persist user message immediately
    await store.append_message(session_id, "user", query)

    yield sse("status", {"phase": "retrieving"})

    chunks = await hybrid_retrieve(query)
    sources = [
        {
            "id": c["id"],
            "source": c["metadata"].get("source", ""),
            "heading": c["metadata"].get("heading", ""),
        }
        for c in chunks
    ]
    yield sse("sources", sources)

    document_context = build_context_block(chunks)

    # Assemble conversation context (previous turns)
    history_messages = await build_context_messages(
        session_id=session_id,
        query=query,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    # Final prompt: system + history + document context + current query
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    messages.extend(history_messages)
    messages.append({
        "role": "user",
        "content": f"Document context:\n{document_context}\n\nQuestion: {query}",
    })

    yield sse("status", {"phase": "generating"})

    config = resolve_provider(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    client = UniversalLLMClient(config)

    accumulated: list[str] = []
    try:
        async for token in client.stream_chat(messages, temperature=temperature):
            accumulated.append(token)
            yield sse("token", {"text": token})
    except Exception as e:
        logger.error("llm_stream_error", extra={"error": str(e), "provider": provider})
        yield sse("error", {"message": str(e)})
        # Persist partial assistant message if any tokens arrived
        if accumulated:
            await store.append_message(session_id, "assistant", "".join(accumulated))
        return

    full_response = "".join(accumulated)
    await store.append_message(session_id, "assistant", full_response)

    yield sse("done", {"chunk_count": len(chunks)})