"""
Deterministic PDF parser using OpenDataLoader PDF.

Requires: Java 11+ (install via apt-get install openjdk-17-jdk in Docker)
Output: Structured JSON with bounding boxes + Markdown for LLM context.
"""
import json
import os
from pathlib import Path
from typing import Any

import opendataloader_pdf

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ParsedDocument:
    """Structured representation of a parsed PDF."""

    def __init__(
        self,
        source_path: str,
        markdown: str,
        structured_json: dict[str, Any],
        images: list[dict[str, Any]] | None = None,
    ):
        self.source_path = source_path
        self.markdown = markdown
        self.structured_json = structured_json
        self.images = images or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "markdown": self.markdown,
            "structured_json": self.structured_json,
            "images": self.images,
        }


def parse_pdf(
    pdf_path: str,
    output_dir: str | None = None,
    hybrid: bool = False,
    force_ocr: bool = False,
    ocr_lang: str | None = None,
) -> ParsedDocument:
    """
    Parse a PDF into structured Markdown + JSON using OpenDataLoader.

    Args:
        pdf_path: Path to the input PDF file.
        output_dir: Where to write intermediate files. Defaults to PARSED_DIR.
        hybrid: Enable hybrid mode for complex tables/charts/OCR.
        force_ocr: Force OCR on all pages (for scanned PDFs).
        ocr_lang: OCR language code (e.g., "en", "ko,en").

    Returns:
        ParsedDocument with markdown, structured JSON, and extracted images.
    """
    pdf_path = str(Path(pdf_path).resolve())
    output_dir = output_dir or settings.parsed_dir
    os.makedirs(output_dir, exist_ok=True)

    stem = Path(pdf_path).stem
    markdown_path = os.path.join(output_dir, f"{stem}.md")
    json_path = os.path.join(output_dir, f"{stem}.json")
    image_dir = os.path.join(output_dir, f"{stem}_images")

    logger.info(
        "parsing_pdf",
        extra={
            "pdf_path": pdf_path,
            "hybrid": hybrid,
            "force_ocr": force_ocr,
        },
    )

    # Build conversion options
    convert_kwargs: dict[str, Any] = {
        "input_path": pdf_path,
        "output_dir": output_dir,
        "format": ["markdown", "json"],
        "image_output": "external",
        "image_dir": image_dir,
        "image_format": "png",
        "quiet": True,
        "content_safety_off": [],  # Keep safety filters ON
    }

    if hybrid:
        convert_kwargs["hybrid"] = "docling-fast"  # or "hancom-ai"
    if force_ocr:
        convert_kwargs["force_ocr"] = True
    if ocr_lang:
        convert_kwargs["ocr_lang"] = ocr_lang

    # Execute conversion
    try:
        opendataloader_pdf.convert(**convert_kwargs)
    except Exception as e:
        logger.error("pdf_parse_failed", extra={"pdf_path": pdf_path, "error": str(e)})
        raise

    # Read Markdown output
    markdown = ""
    if os.path.exists(markdown_path):
        with open(markdown_path, "r", encoding="utf-8") as f:
            markdown = f.read()

    # Read structured JSON output
    structured_json = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            structured_json = json.load(f)

    # Collect extracted images
    images: list[dict[str, Any]] = []
    if os.path.isdir(image_dir):
        for img_file in sorted(os.listdir(image_dir)):
            img_path = os.path.join(image_dir, img_file)
            if os.path.isfile(img_path):
                images.append({
                    "filename": img_file,
                    "path": img_path,
                    "source_pdf": pdf_path,
                })

    logger.info(
        "pdf_parse_complete",
        extra={
            "pdf_path": pdf_path,
            "markdown_length": len(markdown),
            "image_count": len(images),
        },
    )

    return ParsedDocument(
        source_path=pdf_path,
        markdown=markdown,
        structured_json=structured_json,
        images=images,
    )