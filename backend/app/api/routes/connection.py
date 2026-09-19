"""
Provider connection test endpoint.

Frontend calls this before enabling chat so the user sees
"Connected" or "Failed to connect, wrong API".
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.llm_client import resolve_provider, UniversalLLMClient
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["connection"])


class ConnectionTestRequest(BaseModel):
    provider: str = Field(..., description="openai | anthropic | gemini | deepseek | ollama | gguf")
    api_key: str = Field("", description="User-supplied API key (cloud providers only)")
    base_url: str = Field("", description="Local provider URL (ollama/gguf only)")
    model: str = Field("", description="Optional model override")


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    provider: str
    model: str


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connection(req: ConnectionTestRequest):
    """
    Validate provider credentials by issuing a minimal chat request.
    """
    try:
        config = resolve_provider(
            provider=req.provider,
            api_key=req.api_key,
            base_url=req.base_url,
            model=req.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    client = UniversalLLMClient(config)
    success, message = await client.test_connection()

    return ConnectionTestResponse(
        success=success,
        message=message,
        provider=config.name,
        model=config.default_model,
    )


@router.get("/providers")
async def list_providers():
    """Enumerate supported providers for the frontend model selector."""
    return {
        "cloud": [
            {"id": "openai", "label": "OpenAI", "requires_key": True},
            {"id": "anthropic", "label": "Anthropic Claude", "requires_key": True},
            {"id": "gemini", "label": "Google Gemini", "requires_key": True},
            {"id": "deepseek", "label": "DeepSeek", "requires_key": True},
        ],
        "local": [
            {"id": "ollama", "label": "Ollama (local)", "requires_key": False, "requires_url": True},
            {"id": "gguf", "label": "GGUF / llama.cpp (local)", "requires_key": False, "requires_url": True},
        ],
    }