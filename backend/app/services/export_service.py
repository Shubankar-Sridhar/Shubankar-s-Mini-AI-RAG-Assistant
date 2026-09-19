"""
Export chat sessions and summaries as MD / JSON / PDF.
"""
import io
import json
from datetime import datetime
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.logging_config import get_logger

logger = get_logger(__name__)


def export_chat_markdown(session: dict[str, Any]) -> str:
    """Render a chat session as Markdown."""
    lines = [f"# Chat Export — {session.get('session_id', 'unknown')}", ""]
    lines.append(f"_Exported at {datetime.utcnow().isoformat()}Z_")
    lines.append("")
    for msg in session.get("messages", []):
        role = msg.get("role", "user").capitalize()
        lines.append(f"## {role}")
        lines.append("")
        lines.append(msg.get("content", ""))
        lines.append("")
    return "\n".join(lines)


def export_chat_json(session: dict[str, Any]) -> str:
    return json.dumps(session, indent=2, default=str)


def export_chat_pdf(session: dict[str, Any]) -> bytes:
    """Render chat session as a PDF using reportlab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Chat Export — {session.get('session_id', '')}", styles["Title"]))
    story.append(Spacer(1, 12))

    for msg in session.get("messages", []):
        role = msg.get("role", "user").capitalize()
        story.append(Paragraph(f"<b>{role}</b>", styles["Heading3"]))
        content = (msg.get("content") or "").replace("\n", "<br/>")
        story.append(Paragraph(content, styles["BodyText"]))
        story.append(Spacer(1, 8))

    doc.build(story)
    return buffer.getvalue()


def export_summary_markdown(summary: str, session_id: str) -> str:
    return (
        f"# Conversation Summary\n\n"
        f"_Session: {session_id}_\n\n"
        f"_Generated at {datetime.utcnow().isoformat()}Z_\n\n"
        f"{summary}\n"
    )


def export_summary_pdf(summary: str, session_id: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Conversation Summary", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Session: {session_id}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(summary.replace("\n", "<br/>"), styles["BodyText"]),
    ]
    doc.build(story)
    return buffer.getvalue()