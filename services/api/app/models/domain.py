from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SourceName = Literal["reddit", "hacker_news", "discourse"]
ContentType = Literal["thread", "comment", "topic", "post", "story"]


class NormalizedItem(BaseModel):
    source: SourceName
    community: str
    source_item_id: str
    url: str
    title: str
    body: str
    author: str | None = None
    created_at: datetime
    score: float | None = None
    comments_count: int | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    content_type: str
    parent_source_item_id: str | None = None
    ingestion_run_id: int
    ingested_at: datetime
    dedupe_hash: str
    language_signals: list[str] = Field(default_factory=list)
    solution_types: list[str] = Field(default_factory=list)


class IngestionError(BaseModel):
    source: str
    community: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FetchResult(BaseModel):
    items: list[NormalizedItem] = Field(default_factory=list)
    errors: list[IngestionError] = Field(default_factory=list)


class EvidenceRecord(BaseModel):
    category: str
    signal: str
    phrase: str
    snippet: str
    weight: float = 1.0


class ScoreBreakdown(BaseModel):
    pain_intensity_score: float = 0.0
    repetition_score: float = 0.0
    workaround_score: float = 0.0
    self_serve_score: float = 0.0
    build_simplicity_score: float = 0.0
    sales_friction_penalty: float = 0.0
    competition_signal_score: float = 0.0
    overall_opportunity_score: float = 0.0
    rationale: list[str] = Field(default_factory=list)


class TagAssignment(BaseModel):
    name: str
    tag_type: Literal["audience", "problem_type", "solution_type"]


class AnalysisResult(BaseModel):
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    scores: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    tags: list[TagAssignment] = Field(default_factory=list)
    solution_types: list[str] = Field(default_factory=list)
    spam_score: float = 0.0
    is_self_serve_friendly: bool = False

