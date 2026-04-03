from __future__ import annotations

import logging
import sqlite3
from typing import Any

from app.adapters.discourse import DiscourseAdapter
from app.adapters.hacker_news import HackerNewsAdapter
from app.adapters.reddit import RedditAdapter
from app.analysis.opportunity import OpportunityAnalyzer
from app.config.loader import load_app_config
from app.repositories.items import ItemRepository
from app.repositories.runs import RunRepository
from app.services.clustering import ClusterService


logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.config = load_app_config()
        self.items = ItemRepository(conn)
        self.runs = RunRepository(conn)
        self.adapters = {
            "reddit": RedditAdapter(),
            "hacker_news": HackerNewsAdapter(),
            "discourse": DiscourseAdapter(),
        }
        self.analyzer = OpportunityAnalyzer()

    def run(self, sources: list[str] | None = None, limit_override: int | None = None) -> dict[str, Any]:
        enabled = sources or self.config.sources.enabled_sources
        run_id = self.runs.create(enabled, self.config.model_dump(mode="json"))
        existing_items = self.items.get_items_for_analysis(limit=2000)
        total_fetched = 0
        new_item_count = 0
        duplicate_count = 0
        ignored_spam = 0
        errors: list[dict[str, Any]] = []

        for source in enabled:
            adapter = self.adapters.get(source)
            if not adapter:
                errors.append({"source": source, "message": "Unknown source"})
                continue
            try:
                fetch_result = adapter.fetch(run_id=run_id, limit_override=limit_override)
                total_fetched += len(fetch_result.items)
                errors.extend([error.model_dump(mode="json") for error in fetch_result.errors])
                for item in fetch_result.items:
                    if self.items.has_duplicate_hash(item.dedupe_hash, item.source, item.source_item_id):
                        duplicate_count += 1
                        continue
                    analysis = self.analyzer.analyze(item, related_items=existing_items[-250:])
                    if analysis.spam_score >= 2.0:
                        ignored_spam += 1
                        continue
                    _, created = self.items.upsert_item(item, analysis)
                    if created:
                        new_item_count += 1
                    else:
                        duplicate_count += 1
                    existing_items.append(
                        {
                            "title": item.title,
                            "body": item.body,
                            "community": item.community,
                        }
                    )
            except Exception as exc:
                logger.exception("Source ingestion failed")
                errors.append({"source": source, "message": str(exc)})

        cluster_summary = ClusterService(self.conn).refresh()
        status = "completed" if not errors else "completed_with_errors"
        summary = (
            f"Fetched {total_fetched} items, stored {new_item_count}, skipped {duplicate_count} duplicates, "
            f"ignored {ignored_spam} noisy items, and saw {len(errors)} errors."
        )
        self.runs.finish(
            run_id,
            status=status,
            item_count=total_fetched,
            new_item_count=new_item_count,
            duplicate_count=duplicate_count,
            error_count=len(errors),
            summary=summary,
        )
        return {
            "run_id": run_id,
            "status": status,
            "sources": enabled,
            "item_count": total_fetched,
            "new_item_count": new_item_count,
            "duplicate_count": duplicate_count,
            "ignored_spam": ignored_spam,
            "error_count": len(errors),
            "errors": errors,
            "cluster_summary": cluster_summary,
            "summary": summary,
        }
