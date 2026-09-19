"""
Session history and export endpoints.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.session_store import get_session_store
from app.logging_config import get_logger
from app.models.schemas import ExportRequest
from app.services.export_service import (
    export_chat_json,
    export_chat_markdown,
    export_chat_pdf,
    export_summary_markdown,
    export_summary_pdf,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Return the full conversation history for a session."""
    store = get_session_store()
    messages = await store.get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return {"session_id": session_id, "messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    store = get_session_store()
    await store.delete(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.post("/export/chat")
async def export_chat(req: ExportRequest):
    """
    Export a full chat session. format = "md" | "json" | "pdf".
    """
    store = get_session_store()
    messages = await store.get_messages(req.session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty")

    session = {"session_id": req.session_id, "messages": messages}

    if req.format == "md":
        body = export_chat_markdown(session)
        return Response(
            content=body,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="chat_{req.session_id}.md"'},
        )
    if req.format == "json":
        body = export_chat_json(session)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="chat_{req.session_id}.json"'},
        )
    if req.format == "pdf":
        body = export_chat_pdf(session)
        return Response(
            content=body,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="chat_{req.session_id}.pdf"'},
        )
    raise HTTPException(status_code=400, detail="format must be md, json, or pdf")


@router.post("/export/summary")
async def export_summary(req: ExportRequest):
    """
    Export a summary of the session.
    Requires provider credentials so the summary can be generated.
    Only format = "md" | "pdf" supported.
    """
    store = get_session_store()
    messages = await store.get_messages(req.session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty")

    from app.core.llm_client import UniversalLLMClient, resolve_provider

    provider = getattr(req, "provider", "openai")
    api_key = getattr(req, "api_key", "")
    base_url = getattr(req, "base_url", "")
    model = getattr(req, "model", "")

    config = resolve_provider(provider=provider, api_key=api_key, base_url=base_url, model=model)
    client = UniversalLLMClient(config)

    transcript = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in messages
    )
    prompt = (
        "Summarize the following conversation. Preserve all factual content, "
        "names, numbers, and decisions. Do not add information not present.\n\n"
        f"{transcript}"
    )

    chunks: list[str] = []
    async for token in client.stream_chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=500,
    ):
        chunks.append(token)

    summary = "".join(chunks).strip()

    if req.format == "md":
        body = export_summary_markdown(summary, req.session_id)
        return Response(
            content=body,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="summary_{req.session_id}.md"'},
        )
    if req.format == "pdf":
        body = export_summary_pdf(summary, req.session_id)
        return Response(
            content=body,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="summary_{req.session_id}.pdf"'},
        )
    raise HTTPException(status_code=400, detail="format must be md or pdf")