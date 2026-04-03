from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import requests

from app.adapters.base import SourceAdapter
from app.config.loader import load_app_config
from app.models.domain import FetchResult, IngestionError
from app.services.normalizer import Normalizer, clean_html_text, epoch_to_datetime
from app.utils.text import utc_now


logger = logging.getLogger(__name__)


class StackExchangeAdapter(SourceAdapter):
    source_name = "stack_exchange"
    base_url = "https://api.stackexchange.com/2.3"

    def __init__(self) -> None:
        self.config = load_app_config().sources.stack_exchange
        self.defaults = load_app_config().sources.fetch_defaults
        self.normalizer = Normalizer()
        self.session = requests.Session()

    def fetch(self, *, run_id: int, limit_override: int | None = None) -> FetchResult:
        result = FetchResult()
        if not self.config.get("enabled", False):
            return result

        pagesize = self.limit_value(self.config.get("page_size"), limit_override) or 20
        answer_limit = self.limit_value(self.config.get("answer_limit"), limit_override) or 5
        date_window_days = int(self.config.get("date_window_days", self.defaults.get("date_window_days", 30)))
        from_date = int((utc_now() - timedelta(days=date_window_days)).timestamp())
        for query in self.config.get("queries", []):
            site = query["site"]
            community = query.get("community") or f"{site}:{query.get('tags', '') or 'general'}"
            params = {
                "site": site,
                "pagesize": pagesize,
                "sort": query.get("sort", "votes"),
                "order": query.get("order", "desc"),
                "fromdate": from_date,
                "filter": "withbody",
            }
            if query.get("tags"):
                params["tagged"] = query["tags"]
            if query.get("intitle"):
                params["intitle"] = query["intitle"]
            try:
                payload = self._get_json("/questions", params=params)
                for question in payload.get("items", []):
                    result.items.append(
                        self.normalizer.normalize(
                            source=self.source_name,
                            ingestion_method="api_stackexchange",
                            community=community,
                            source_item_id=f"{site}:q:{question['question_id']}",
                            url=question["link"],
                            title=question.get("title"),
                            body=clean_html_text(question.get("body")),
                            author=(question.get("owner") or {}).get("display_name"),
                            created_at=epoch_to_datetime(question.get("creation_date")),
                            score=float(question.get("score") or 0),
                            comments_count=int(question.get("answer_count") or 0),
                            raw_metadata={
                                "site": site,
                                "tags": question.get("tags", []),
                                "is_answered": question.get("is_answered"),
                                "view_count": question.get("view_count"),
                            },
                            content_type="thread",
                            parent_source_item_id=None,
                            ingestion_run_id=run_id,
                        )
                    )
                    if not question.get("answer_count"):
                        continue
                    answers = self._get_json(
                        f"/questions/{question['question_id']}/answers",
                        params={
                            "site": site,
                            "pagesize": answer_limit,
                            "sort": "votes",
                            "order": "desc",
                            "filter": "withbody",
                        },
                    )
                    for answer in answers.get("items", []):
                        result.items.append(
                            self.normalizer.normalize(
                                source=self.source_name,
                                ingestion_method="api_stackexchange",
                                community=community,
                                source_item_id=f"{site}:a:{answer['answer_id']}",
                                url=answer["link"],
                                title=f"Answer on: {question.get('title', 'Stack Exchange question')}",
                                body=clean_html_text(answer.get("body")),
                                author=(answer.get("owner") or {}).get("display_name"),
                                created_at=epoch_to_datetime(answer.get("creation_date")),
                                score=float(answer.get("score") or 0),
                                comments_count=int(answer.get("comment_count") or 0),
                                raw_metadata={
                                    "site": site,
                                    "question_id": question["question_id"],
                                    "is_accepted": answer.get("is_accepted"),
                                },
                                content_type="comment",
                                parent_source_item_id=f"{site}:q:{question['question_id']}",
                                ingestion_run_id=run_id,
                            )
                        )
            except Exception as exc:
                logger.exception("Stack Exchange fetch failed")
                result.errors.append(
                    IngestionError(
                        source=self.source_name,
                        ingestion_method="api_stackexchange",
                        community=community,
                        message=str(exc),
                        metadata={"site": site},
                    )
                )
        return result

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

