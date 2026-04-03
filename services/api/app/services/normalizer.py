from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dateutil import parser as date_parser

from app.models.domain import NormalizedItem
from app.utils.text import compact_whitespace, make_dedupe_hash, utc_now


def epoch_to_datetime(value: int | float | None) -> datetime:
    if value is None:
        return utc_now()
    return datetime.fromtimestamp(value, tz=timezone.utc)


def parse_discourse_datetime(value: str | None) -> datetime:
    if not value:
        return utc_now()
    parsed = date_parser.parse(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def clean_html_text(value: str | None) -> str:
    if not value:
        return ""
    text = value
    replacements = {
        "<p>": " ",
        "</p>": " ",
        "<br>": " ",
        "<br/>": " ",
        "<br />": " ",
        "</li>": " ",
        "<li>": " ",
        "</ul>": " ",
        "<ul>": " ",
        "</ol>": " ",
        "<ol>": " ",
        "</code>": " ",
        "<code>": " ",
        "</pre>": " ",
        "<pre>": " ",
        "&nbsp;": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    while "<" in text and ">" in text:
        start = text.find("<")
        end = text.find(">", start)
        if end == -1:
            break
        text = f"{text[:start]} {text[end + 1:]}"
    return compact_whitespace(text)


class Normalizer:
    def normalize(
        self,
        *,
        source: str,
        ingestion_method: str,
        community: str,
        source_item_id: str,
        url: str,
        title: str | None,
        body: str | None,
        author: str | None,
        created_at: datetime,
        score: float | None,
        comments_count: int | None,
        raw_metadata: dict[str, Any],
        content_type: str,
        parent_source_item_id: str | None,
        ingestion_run_id: int,
    ) -> NormalizedItem:
        title_text = compact_whitespace(title or "")
        body_text = compact_whitespace(body or "")
        dedupe_hash = make_dedupe_hash(community, title_text, body_text)
        return NormalizedItem(
            source=source,
            ingestion_method=ingestion_method,
            community=community,
            source_item_id=source_item_id,
            url=url,
            title=title_text,
            body=body_text,
            author=author,
            created_at=created_at,
            score=score,
            comments_count=comments_count,
            raw_metadata=raw_metadata,
            content_type=content_type,
            parent_source_item_id=parent_source_item_id,
            ingestion_run_id=ingestion_run_id,
            ingested_at=utc_now(),
            dedupe_hash=dedupe_hash,
        )
