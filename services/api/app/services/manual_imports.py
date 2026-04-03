from __future__ import annotations

import sqlite3
from urllib.parse import urlparse

from app.analysis.opportunity import OpportunityAnalyzer
from app.models.api import ManualRedditImportRequest
from app.repositories.items import ItemRepository
from app.repositories.runs import RunRepository
from app.services.clustering import ClusterService
from app.services.normalizer import Normalizer
from app.utils.text import make_short_hash, utc_now


class ManualImportService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.items = ItemRepository(conn)
        self.runs = RunRepository(conn)
        self.normalizer = Normalizer()
        self.analyzer = OpportunityAnalyzer()

    def import_reddit_threads(self, request: ManualRedditImportRequest) -> dict[str, object]:
        run_id = self.runs.create(["reddit"], {"manual_import": True}, "manual_reddit_url")
        existing_items = self.items.get_items_for_analysis(limit=2000)
        item_count = 0
        new_item_count = 0
        duplicate_count = 0
        ignored_spam = 0

        for thread in request.threads:
            thread_item = self.normalizer.normalize(
                source="reddit",
                ingestion_method="manual_reddit_url",
                community=thread.community,
                source_item_id=self._thread_source_item_id(thread.url),
                url=thread.url,
                title=thread.title,
                body=thread.body,
                author=thread.author,
                created_at=thread.created_at or utc_now(),
                score=thread.score,
                comments_count=thread.comments_count if thread.comments_count is not None else len(thread.comments),
                raw_metadata={
                    "original_url": thread.url,
                    "capture_format": "manual_url_import",
                    "imported_comment_count": len(thread.comments),
                    "missing_fields_supplied": [
                        name
                        for name, value in {
                            "author": thread.author,
                            "created_at": thread.created_at,
                            "score": thread.score,
                            "comments_count": thread.comments_count,
                        }.items()
                        if value is None
                    ],
                },
                content_type="thread",
                parent_source_item_id=None,
                ingestion_run_id=run_id,
            )
            item_count += 1
            if self.items.has_duplicate_hash(thread_item.dedupe_hash, thread_item.source, thread_item.source_item_id):
                duplicate_count += 1
            else:
                analysis = self.analyzer.analyze(thread_item, related_items=existing_items[-250:])
                if analysis.spam_score >= 2.0:
                    ignored_spam += 1
                else:
                    _, created = self.items.upsert_item(thread_item, analysis)
                    if created:
                        new_item_count += 1
                    else:
                        duplicate_count += 1
                    existing_items.append({"title": thread_item.title, "body": thread_item.body, "community": thread_item.community})

            thread_source_item_id = thread_item.source_item_id
            for index, comment in enumerate(thread.comments, start=1):
                comment_item = self.normalizer.normalize(
                    source="reddit",
                    ingestion_method="manual_reddit_url",
                    community=thread.community,
                    source_item_id=f"{thread_source_item_id}:comment:{index}:{make_short_hash(comment.body, comment.author or '')}",
                    url=thread.url,
                    title=f"Comment on: {thread.title}",
                    body=comment.body,
                    author=comment.author,
                    created_at=comment.created_at or thread.created_at or utc_now(),
                    score=comment.score,
                    comments_count=None,
                    raw_metadata={
                        "original_url": thread.url,
                        "capture_format": "manual_url_import",
                        "manual_comment_index": index,
                    },
                    content_type="comment",
                    parent_source_item_id=thread_source_item_id,
                    ingestion_run_id=run_id,
                )
                item_count += 1
                if self.items.has_duplicate_hash(comment_item.dedupe_hash, comment_item.source, comment_item.source_item_id):
                    duplicate_count += 1
                    continue
                analysis = self.analyzer.analyze(comment_item, related_items=existing_items[-250:])
                if analysis.spam_score >= 2.0:
                    ignored_spam += 1
                    continue
                _, created = self.items.upsert_item(comment_item, analysis)
                if created:
                    new_item_count += 1
                else:
                    duplicate_count += 1
                existing_items.append({"title": comment_item.title, "body": comment_item.body, "community": comment_item.community})

        cluster_summary = ClusterService(self.conn).refresh()
        summary = (
            f"Imported {item_count} manual Reddit items, stored {new_item_count}, "
            f"skipped {duplicate_count} duplicates, and ignored {ignored_spam} noisy items."
        )
        self.runs.finish(
            run_id,
            status="completed",
            item_count=item_count,
            new_item_count=new_item_count,
            duplicate_count=duplicate_count,
            error_count=0,
            summary=summary,
        )
        return {
            "run_id": run_id,
            "status": "completed",
            "item_count": item_count,
            "new_item_count": new_item_count,
            "duplicate_count": duplicate_count,
            "ignored_spam": ignored_spam,
            "cluster_summary": cluster_summary,
            "summary": summary,
        }

    def template_payload(self) -> dict[str, object]:
        return {
            "threads": [
                {
                    "url": "https://www.reddit.com/r/parenting/comments/example/thread_slug/",
                    "community": "parenting",
                    "title": "Wish there was an easier way to coordinate school pickup",
                    "body": "I keep updating a spreadsheet and texting everyone manually.",
                    "author": "throwaway_parent",
                    "created_at": "2026-04-03T12:00:00Z",
                    "score": 128,
                    "comments_count": 2,
                    "comments": [
                        {
                            "body": "We do this with a shared note and it is still a mess.",
                            "author": "another_parent",
                            "created_at": "2026-04-03T13:00:00Z",
                            "score": 14,
                        }
                    ],
                }
            ]
        }

    def _thread_source_item_id(self, url: str) -> str:
        path_parts = [part for part in urlparse(url).path.split("/") if part]
        if "comments" in path_parts:
            try:
                return f"manual:{path_parts[path_parts.index('comments') + 1]}"
            except IndexError:
                pass
        return f"manual:{make_short_hash(url)}"

