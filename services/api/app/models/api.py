from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IngestionRequest(BaseModel):
    sources: list[str] | None = None
    limit_override: int | None = None


class ItemUpdateRequest(BaseModel):
    saved: bool | None = None
    dismissed: bool | None = None
    notes: str | None = None


class ExportFormat(str):
    CSV = "csv"
    MARKDOWN = "markdown"


class ItemListResponse(BaseModel):
    total: int
    items: list[dict[str, Any]]


class RunResponse(BaseModel):
    id: int
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    item_count: int = 0
    new_item_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    sources: list[str] = Field(default_factory=list)
    summary: str | None = None


class ClusterResponse(BaseModel):
    id: int
    label: str
    description: str | None = None
    key_terms: list[str] = Field(default_factory=list)
    item_count: int = 0
    avg_score: float | None = None


class MarkdownSummaryRequest(BaseModel):
    limit: int = 20
    min_score: float = 0.0


class MarkdownSummaryResponse(BaseModel):
    markdown: str
    generated_at: datetime

