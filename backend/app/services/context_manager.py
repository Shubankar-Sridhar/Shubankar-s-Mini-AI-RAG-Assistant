"""
Context assembly for multi-turn conversations.

Strategy:
- Always include the last HOT_WINDOW_SIZE messages.
- For older messages, recall the top-K most semantically similar to the query.
- If history is long, produce a rolling summary of the oldest half and
  persist it in Redis as a single "summary" message.
"""
import json
from typing import Any

from app.config import get_settings
from app.core.cache import get_l2
from app.core.embeddings import embed_texts
from app.core.llm_client import UniversalLLMClient, resolve_provider
from app.core.session_store import get_session_store
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


SUMMARY_PROMPT = (
    "Summarize the following conversation excerpt concisely. "
    "Preserve all factual content, names, numbers, and decisions. "
    "Do not add information not present in the excerpt."
)


async def _summarize_messages(
    messages: list[dict[str, Any]],
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    """Compress a batch of messages into a single summary string."""
    transcript_lines = [
        f"{m['role'].capitalize()}: {m['content']}"
        for m in messages
    ]
    transcript = "\n".join(transcript_lines)

    config = resolve_provider(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    client = UniversalLLMClient(config)

    chunks: list[str] = []
    try:
        async for token in client.stream_chat(
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": transcript},
            ],
            temperature=0.0,
            max_tokens=400,
        ):
            chunks.append(token)
    except Exception as e:
        logger.error("summarization_failed", extra={"error": str(e)})
        return ""

    return "".join(chunks).strip()


async def _semantic_recall(
    query: str,
    older_messages: list[dict[str, Any]],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Return the top-K older messages most similar to the query.
    Uses in-process cosine similarity over freshly computed embeddings.
    """
    if not older_messages:
        return []

    texts = [m["content"] for m in older_messages]
    try:
        all_embeddings = await embed_texts([query] + texts)
    except Exception as e:
        logger.warning("semantic_recall_embed_failed", extra={"error": str(e)})
        return older_messages[-top_k:]

    query_vec = all_embeddings[0]
    msg_vecs = all_embeddings[1:]

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    scored = [
        (cosine(query_vec, vec), idx)
        for idx, vec in enumerate(msg_vecs)
    ]
    scored.sort(reverse=True)
    top_indices = sorted(idx for _, idx in scored[:top_k])
    return [older_messages[i] for i in top_indices]


async def build_context_messages(
    session_id: str,
    query: str,
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
) -> list[dict[str, Any]]:
    """
    Produce the list of OpenAI-format messages to send to the LLM.

    Order: [system, summary(if any), recalled older, hot window..., current user]
    """
    store = get_session_store()
    history = await store.get_messages(session_id)

    if not history:
        return []

    hot_size = settings.hot_window_size
    if len(history) <= hot_size:
        return [{"role": m["role"], "content": m["content"]} for m in history]

    older = history[:-hot_size]
    hot = history[-hot_size:]

    # Rolling summary when older section grows too large
    summary_text: str | None = None
    if len(older) >= settings.summarization_threshold * 2:
        cache_key = f"summary:{session_id}:{len(older)}"
        l2 = get_l2()
        cached = await l2.get(cache_key)
        if cached and isinstance(cached, dict):
            summary_text = cached.get("summary")

        if not summary_text:
            summary_text = await _summarize_messages(
                older, provider, api_key, base_url, model
            )
            if summary_text:
                await l2.set(cache_key, {"summary": summary_text})
        older_for_recall = older[-settings.summarization_threshold:]
    else:
        older_for_recall = older

    recalled = await _semantic_recall(query, older_for_recall, top_k=3)

    assembled: list[dict[str, Any]] = []
    if summary_text:
        assembled.append({
            "role": "system",
            "content": f"Earlier conversation summary:\n{summary_text}",
        })
    for m in recalled:
        assembled.append({"role": m["role"], "content": m["content"]})
    for m in hot:
        assembled.append({"role": m["role"], "content": m["content"]})

    logger.info(
        "context_assembled",
        extra={
            "session_id": session_id,
            "total_history": len(history),
            "recalled": len(recalled),
            "hot": len(hot),
            "has_summary": bool(summary_text),
        },
    )
    return assembled