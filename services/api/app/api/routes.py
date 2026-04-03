from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
import sqlite3

from app.api.dependencies import get_db
from app.models.api import IngestionRequest, ItemUpdateRequest, ManualRedditImportRequest, MarkdownSummaryRequest
from app.repositories.items import ItemRepository
from app.repositories.runs import RunRepository
from app.services.clustering import ClusterService
from app.services.ingestion import IngestionService
from app.services.manual_imports import ManualImportService
from app.services.summary import SummaryService


router = APIRouter(prefix="/api")


def _filters(
    keyword: str | None = Query(default=None),
    query: str | None = Query(default=None),
    source: str | None = Query(default=None),
    ingestion_method: str | None = Query(default=None),
    candidate_only: bool = Query(default=True),
    include_supporting: bool = Query(default=False),
    content_role: str | None = Query(default=None),
    community: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    tag_type: str | None = Query(default=None),
    solution_type: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    self_serve_only: bool = Query(default=False),
    saved_only: bool = Query(default=False),
    dismissed_only: bool = Query(default=False),
    sort_by: str = Query(default="overall_score"),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return {
        "keyword": keyword,
        "query": query,
        "source": source,
        "ingestion_method": ingestion_method,
        "candidate_only": candidate_only,
        "include_supporting": include_supporting,
        "content_role": content_role,
        "community": community,
        "tag": tag,
        "tag_type": tag_type,
        "solution_type": solution_type,
        "start_date": start_date,
        "end_date": end_date,
        "min_score": min_score,
        "self_serve_only": self_serve_only,
        "saved_only": saved_only,
        "dismissed_only": dismissed_only,
        "sort_by": sort_by,
        "limit": limit,
        "offset": offset,
    }


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/runs/ingest")
def run_ingestion(request: IngestionRequest, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    service = IngestionService(db)
    return service.run(sources=request.sources, limit_override=request.limit_override)


@router.get("/imports/reddit-template")
def reddit_import_template(db: sqlite3.Connection = Depends(get_db)) -> dict[str, object]:
    return ManualImportService(db).template_payload()


@router.post("/imports/reddit-manual")
def import_reddit_manual(
    request: ManualRedditImportRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, object]:
    return ManualImportService(db).import_reddit_threads(request)


@router.get("/runs")
def list_runs(limit: int = Query(default=20, le=100), db: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    return RunRepository(db).list_runs(limit=limit)


@router.get("/items")
def list_items(
    filters: dict[str, Any] = Depends(_filters),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    total, items = ItemRepository(db).query_items(filters)
    return {"total": total, "items": items}


@router.get("/items/{item_id}")
def get_item(item_id: int, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    item = ItemRepository(db).get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/items/{item_id}")
def update_item(
    item_id: int,
    request: ItemUpdateRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    payload = request.model_dump(exclude_none=True)
    repo = ItemRepository(db)
    repo.update_item(item_id, payload)
    item = repo.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/clusters")
def list_clusters(limit: int = Query(default=50, le=100), db: sqlite3.Connection = Depends(get_db)) -> list[dict[str, Any]]:
    return ItemRepository(db).list_clusters(limit=limit)


@router.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: int, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    cluster = ItemRepository(db).get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.post("/clusters/refresh")
def refresh_clusters(db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    return ClusterService(db).refresh()


@router.get("/stats")
def get_stats(db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    return ItemRepository(db).get_stats()


@router.get("/export")
def export_results(
    format: str = Query(default="csv", pattern="^(csv|markdown)$"),
    filters: dict[str, Any] = Depends(_filters),
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    content = ItemRepository(db).export_items(filters, format)
    media_type = "text/markdown" if format == "markdown" else "text/csv"
    return Response(content=content, media_type=media_type)


@router.post("/summaries/markdown")
def markdown_summary(
    request: MarkdownSummaryRequest,
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    return SummaryService(db).generate_markdown(limit=request.limit, min_score=request.min_score)
