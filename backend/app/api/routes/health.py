"""Health and readiness endpoints."""
from fastapi import APIRouter

from app.config import get_settings
from app.core.retriever import get_vector_store
from app.logging_config import get_logger
from app.models.schemas import HealthResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness + dependency check for the backend."""
    chroma_ok = False
    try:
        chroma_ok = get_vector_store().heartbeat()
    except Exception as e:
        logger.warning("health_chroma_failed", extra={"error": str(e)})

    return HealthResponse(
        status="healthy",
        env=settings.app_env,
        version="0.1.0",
        chroma_ok=chroma_ok,
    )