from __future__ import annotations

import logging

import feedparser

from app.adapters.base import SourceAdapter
from app.config.loader import load_app_config
from app.models.domain import FetchResult, IngestionError
from app.services.normalizer import Normalizer, clean_html_text, parse_discourse_datetime
from app.utils.text import make_short_hash


logger = logging.getLogger(__name__)


class GenericRssAdapter(SourceAdapter):
    source_name = "rss_generic"

    def __init__(self) -> None:
        self.config = load_app_config().sources.rss_feeds
        self.normalizer = Normalizer()

    def fetch(self, *, run_id: int, limit_override: int | None = None) -> FetchResult:
        result = FetchResult()
        if not self.config.get("enabled", False):
            return result
        for feed in self.config.get("feeds", []):
            item_limit = self.limit_value(feed.get("limit"), limit_override) or 20
            try:
                parsed = feedparser.parse(feed["feed_url"])
                for entry in parsed.entries[:item_limit]:
                    link = entry.get("link") or feed["feed_url"]
                    result.items.append(
                        self.normalizer.normalize(
                            source=self.source_name,
                            ingestion_method="rss_generic",
                            community=feed["name"],
                            source_item_id=f"{feed['name']}:rss:{make_short_hash(link, entry.get('id', ''))}",
                            url=link,
                            title=entry.get("title") or f"{feed['name']} item",
                            body=clean_html_text(entry.get("summary") or entry.get("description")),
                            author=entry.get("author"),
                            created_at=parse_discourse_datetime(entry.get("published") or entry.get("updated")),
                            score=None,
                            comments_count=None,
                            raw_metadata={
                                "feed_url": feed["feed_url"],
                                "source_label": feed.get("source_label", feed["name"]),
                            },
                            content_type="topic",
                            parent_source_item_id=None,
                            ingestion_run_id=run_id,
                        )
                    )
            except Exception as exc:
                logger.exception("Generic RSS fetch failed")
                result.errors.append(
                    IngestionError(
                        source=self.source_name,
                        ingestion_method="rss_generic",
                        community=feed["name"],
                        message=str(exc),
                        metadata={"feed_url": feed["feed_url"]},
                    )
                )
        return result

