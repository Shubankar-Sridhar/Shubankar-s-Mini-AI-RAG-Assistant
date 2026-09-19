"""Pydantic schemas for API request and response payloads."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    env: str
    version: str
    chroma_ok: bool


class UploadResponse(BaseModel):
    status: str
    filename: str
    chunk_count: int
    image_count: int
    markdown_path: str | None = None


class SourceCitation(BaseModel):
    id: str
    source: str
    heading: str = ""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExportRequest(BaseModel):
    session_id: str
    format: str = "md"  # "md" | "pdf" | "json"
    provider: str = "openai"
    api_key: str = ""
    base_url: str = ""
    model: str = ""


class SummaryRequest(BaseModel):
    session_id: str
    provider: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""