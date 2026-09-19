"""PDF upload and ingestion endpoint."""
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.logging_config import get_logger
from app.models.schemas import UploadResponse
from app.services.ingestion import ingest_pdf

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])
settings = get_settings()

ALLOWED_MIME = {"application/pdf"}


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accept a PDF, persist to disk, run ingestion pipeline.
    """
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    dest = os.path.join(settings.upload_dir, safe_name)

    # Stream to disk with size guard
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    written = 0
    try:
        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    f.close()
                    os.remove(dest)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("upload_write_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to store file")

    try:
        result = await ingest_pdf(dest)
    except Exception as e:
        logger.error("ingestion_failed", extra={"error": str(e), "path": dest})
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return UploadResponse(
        status=result["status"],
        filename=file.filename or safe_name,
        chunk_count=result.get("chunk_count", 0),
        image_count=result.get("image_count", 0),
        markdown_path=result.get("markdown_path"),
    )