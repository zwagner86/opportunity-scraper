from __future__ import annotations

import logging
from urllib.parse import urljoin

import feedparser
import requests

from app.adapters.base import SourceAdapter
from app.config.loader import load_app_config
from app.models.domain import FetchResult, IngestionError
from app.services.normalizer import Normalizer, clean_html_text, parse_discourse_datetime


logger = logging.getLogger(__name__)


class DiscourseAdapter(SourceAdapter):
    source_name = "discourse"

    def __init__(self) -> None:
        self.config = load_app_config().sources.discourse
        self.normalizer = Normalizer()
        self.session = requests.Session()

    def fetch(self, *, run_id: int, limit_override: int | None = None) -> FetchResult:
        result = FetchResult()
        if not self.config.get("enabled", False):
            return result
        for forum in self.config.get("forums", []):
            try:
                if forum.get("mode", "json") == "json":
                    self._fetch_json(result, forum, run_id, limit_override)
                else:
                    self._fetch_rss(result, forum, run_id, limit_override)
            except Exception as exc:
                logger.exception("Discourse fetch failed")
                result.errors.append(
                    IngestionError(
                        source=self.source_name,
                        ingestion_method="json_discourse" if forum.get("mode", "json") == "json" else "rss_discourse",
                        community=forum["name"],
                        message=str(exc),
                    )
                )
        return result

    def _fetch_json(
        self,
        result: FetchResult,
        forum: dict,
        run_id: int,
        limit_override: int | None,
    ) -> None:
        topic_limit = self.limit_value(forum.get("latest_limit"), limit_override) or 20
        comment_limit = self.limit_value(forum.get("comment_limit"), limit_override) or 10
        latest = self.session.get(urljoin(forum["base_url"], "/latest.json"), timeout=20)
        latest.raise_for_status()
        topics = latest.json().get("topic_list", {}).get("topics", [])[:topic_limit]
        for topic in topics:
            topic_id = topic["id"]
            slug = topic.get("slug") or str(topic_id)
            topic_response = self.session.get(
                urljoin(forum["base_url"], f"/t/{slug}/{topic_id}.json"),
                timeout=20,
            )
            topic_response.raise_for_status()
            payload = topic_response.json()
            posts = payload.get("post_stream", {}).get("posts", [])
            first_post = posts[0] if posts else {}
            result.items.append(
                self.normalizer.normalize(
                    source=self.source_name,
                    ingestion_method="json_discourse",
                    community=forum["name"],
                    source_item_id=f"{forum['name']}:topic:{topic_id}",
                    url=urljoin(forum["base_url"], f"/t/{slug}/{topic_id}"),
                    title=payload.get("title") or topic.get("title") or "Untitled topic",
                    body=clean_html_text(first_post.get("cooked")),
                    author=first_post.get("username"),
                    created_at=parse_discourse_datetime(first_post.get("created_at")),
                    score=float(topic.get("like_count") or 0),
                    comments_count=max(0, int(topic.get("posts_count") or 1) - 1),
                    raw_metadata={
                        "forum": forum["name"],
                        "tags": topic.get("tags", []),
                        "views": topic.get("views"),
                        "category_id": topic.get("category_id"),
                    },
                    content_type="topic",
                    parent_source_item_id=None,
                    ingestion_run_id=run_id,
                )
            )
            for post in posts[1:comment_limit + 1]:
                result.items.append(
                    self.normalizer.normalize(
                        source=self.source_name,
                        ingestion_method="json_discourse",
                        community=forum["name"],
                        source_item_id=f"{forum['name']}:post:{post['id']}",
                        url=urljoin(forum["base_url"], f"/t/{slug}/{topic_id}/{post.get('post_number', 1)}"),
                        title=f"Reply on: {payload.get('title') or topic.get('title')}",
                        body=clean_html_text(post.get("cooked")),
                        author=post.get("username"),
                        created_at=parse_discourse_datetime(post.get("created_at")),
                        score=float(post.get("reply_count") or 0),
                        comments_count=int(post.get("reply_count") or 0),
                        raw_metadata={
                            "forum": forum["name"],
                            "topic_id": topic_id,
                            "post_number": post.get("post_number"),
                            "reply_to_post_number": post.get("reply_to_post_number"),
                        },
                        content_type="post",
                        parent_source_item_id=f"{forum['name']}:topic:{topic_id}",
                        ingestion_run_id=run_id,
                    )
                )

    def _fetch_rss(
        self,
        result: FetchResult,
        forum: dict,
        run_id: int,
        limit_override: int | None,
    ) -> None:
        topic_limit = self.limit_value(forum.get("latest_limit"), limit_override) or 20
        feed_url = forum.get("feed_url") or urljoin(forum["base_url"], "/latest.rss")
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:topic_limit]:
            result.items.append(
                self.normalizer.normalize(
                    source=self.source_name,
                    ingestion_method="rss_discourse",
                    community=forum["name"],
                    source_item_id=f"{forum['name']}:rss:{entry.get('id', entry.get('link'))}",
                    url=entry.get("link"),
                    title=entry.get("title"),
                    body=clean_html_text(entry.get("summary")),
                    author=entry.get("author"),
                    created_at=parse_discourse_datetime(entry.get("published")),
                    score=None,
                    comments_count=None,
                    raw_metadata={"forum": forum["name"], "feed_url": feed_url},
                    content_type="topic",
                    parent_source_item_id=None,
                    ingestion_run_id=run_id,
                )
            )
