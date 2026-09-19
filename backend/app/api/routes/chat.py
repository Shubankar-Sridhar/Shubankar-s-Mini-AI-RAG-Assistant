"""
Chat SSE endpoint using the universal LLM client.
"""
from fastapi import APIRouter, Request
from sse_starlette import EventSourceResponse

from app.core.session_store import get_session_store
from app.services.chat_service import stream_chat_response, sse
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/chat/stream")
async def chat_stream(
    request: Request,
    query: str,
    session_id: str = "",
    provider: str = "openai",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    temperature: float = 0.2,
):
    """
    SSE endpoint. Frontend connects via EventSource with query params.
    If session_id is empty, a new one is created and emitted as the
    first event so the client can reuse it on subsequent turns.
    """
    store = get_session_store()
    resolved_session_id = session_id or store.new_session_id()

    async def event_generator():
        yield sse("session", {"session_id": resolved_session_id})

        async for event in stream_chat_response(
            query=query,
            session_id=resolved_session_id,
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
        ):
            if await request.is_disconnected():
                logger.info("client_disconnected", extra={"session_id": resolved_session_id})
                break
            yield event

    return EventSourceResponse(event_generator(), ping=15)