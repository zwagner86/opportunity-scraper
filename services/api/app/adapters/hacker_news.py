from __future__ import annotations

import logging
from typing import Any

import requests

from app.adapters.base import SourceAdapter
from app.config.loader import load_app_config
from app.models.domain import FetchResult, IngestionError
from app.services.normalizer import Normalizer, clean_html_text, epoch_to_datetime


logger = logging.getLogger(__name__)


class HackerNewsAdapter(SourceAdapter):
    source_name = "hacker_news"
    base_url = "https://hacker-news.firebaseio.com/v0"

    def __init__(self) -> None:
        self.config = load_app_config().sources.hacker_news
        self.normalizer = Normalizer()
        self.session = requests.Session()

    def fetch(self, *, run_id: int, limit_override: int | None = None) -> FetchResult:
        result = FetchResult()
        if not self.config.get("enabled", False):
            return result
        per_feed_limit = self.limit_value(self.config.get("per_feed_limit"), limit_override) or 30
        comment_limit = self.limit_value(self.config.get("comment_limit"), limit_override) or 20
        for feed in self.config.get("feeds", []):
            try:
                ids = self._get_json(f"{self.base_url}/{feed}stories.json")[:per_feed_limit]
                for item_id in ids:
                    story = self._get_json(f"{self.base_url}/item/{item_id}.json")
                    if not story or story.get("deleted") or story.get("dead"):
                        continue
                    title = story.get("title") or "Untitled HN story"
                    body = clean_html_text(story.get("text"))
                    url = story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}"
                    result.items.append(
                        self.normalizer.normalize(
                            source=self.source_name,
                            ingestion_method="api_hacker_news",
                            community=feed,
                            source_item_id=str(story["id"]),
                            url=url,
                            title=title,
                            body=body,
                            author=story.get("by"),
                            created_at=epoch_to_datetime(story.get("time")),
                            score=float(story.get("score") or 0),
                            comments_count=int(story.get("descendants") or 0),
                            raw_metadata={"feed": feed, "kids": story.get("kids", [])},
                            content_type="story",
                            parent_source_item_id=None,
                            ingestion_run_id=run_id,
                        )
                    )
                    for comment_id in (story.get("kids") or [])[:comment_limit]:
                        comment = self._get_json(f"{self.base_url}/item/{comment_id}.json")
                        if not comment or comment.get("deleted") or comment.get("dead"):
                            continue
                        comment_text = clean_html_text(comment.get("text"))
                        if not comment_text:
                            continue
                        result.items.append(
                            self.normalizer.normalize(
                                source=self.source_name,
                                ingestion_method="api_hacker_news",
                                community=feed,
                                source_item_id=str(comment["id"]),
                                url=f"https://news.ycombinator.com/item?id={comment['id']}",
                                title=f"Comment on: {title}",
                                body=comment_text,
                                author=comment.get("by"),
                                created_at=epoch_to_datetime(comment.get("time")),
                                score=None,
                                comments_count=len(comment.get("kids") or []),
                                raw_metadata={
                                    "feed": feed,
                                    "story_id": story["id"],
                                    "parent_id": comment.get("parent"),
                                    "kids": comment.get("kids", []),
                                },
                                content_type="comment",
                                parent_source_item_id=str(story["id"]),
                                ingestion_run_id=run_id,
                            )
                        )
            except Exception as exc:
                logger.exception("HN fetch failed")
                result.errors.append(
                    IngestionError(
                        source=self.source_name,
                        ingestion_method="api_hacker_news",
                        community=feed,
                        message=str(exc),
                    )
                )
        return result

    def _get_json(self, url: str) -> Any:
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.json()
