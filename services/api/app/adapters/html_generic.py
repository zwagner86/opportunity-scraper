from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin

import requests

from app.adapters.base import SourceAdapter
from app.config.loader import load_app_config
from app.models.domain import FetchResult, IngestionError
from app.services.normalizer import Normalizer, parse_discourse_datetime
from app.utils.html import HtmlNode, parse_html_document, select_all, select_first
from app.utils.text import compact_whitespace, make_short_hash, utc_now


logger = logging.getLogger(__name__)
INTEGER_RE = re.compile(r"\d+")


class HtmlGenericAdapter(SourceAdapter):
    source_name = "html_generic"

    def __init__(self) -> None:
        self.config = load_app_config().sources.html_generic
        self.normalizer = Normalizer()
        self.session = requests.Session()

    def fetch(self, *, run_id: int, limit_override: int | None = None) -> FetchResult:
        result = FetchResult()
        if not self.config.get("enabled", False):
            return result

        base_headers = self.config.get("request_headers", {})
        for source in self.config.get("sources", []):
            item_limit = self.limit_value(source.get("limit"), limit_override) or 20
            try:
                html = self._get_text(source["list_url"], headers={**base_headers, **source.get("request_headers", {})})
                document = parse_html_document(html)
                item_nodes = self._select_nodes(document, source["item_selector"])[:item_limit]
                for node in item_nodes:
                    normalized = self._normalize_source_item(source=source, node=node, run_id=run_id, base_headers=base_headers)
                    if normalized:
                        result.items.append(normalized)
            except Exception as exc:
                logger.exception("HTML source fetch failed")
                result.errors.append(
                    IngestionError(
                        source=self.source_name,
                        ingestion_method="html_generic",
                        community=source.get("community") or source.get("name"),
                        message=str(exc),
                        metadata={"list_url": source.get("list_url"), "source_name": source.get("name")},
                    )
                )
        return result

    def _normalize_source_item(
        self,
        *,
        source: dict[str, Any],
        node: HtmlNode,
        run_id: int,
        base_headers: dict[str, str],
    ):
        title_node = self._select_node(node, source.get("title_selector"))
        link_node = self._select_node(node, source.get("link_selector") or source.get("title_selector"))
        title = compact_whitespace(self._node_text(title_node) or self._node_text(link_node))
        link_value = self._node_attr(link_node, source.get("link_attr", "href"))
        if not title or not link_value:
            return None

        detail_url = urljoin(source["list_url"], link_value)
        body = self._node_text(self._select_node(node, source.get("summary_selector")))
        author = self._node_text(self._select_node(node, source.get("author_selector"))) or None
        community = compact_whitespace(source.get("community") or self._node_text(self._select_node(node, source.get("community_selector")))) or source.get("name", "html")
        created_at = self._safe_datetime(
            self._node_value(node, source.get("date_selector"), source.get("date_attr"))
        )
        comments_count = self._parse_integer(
            self._node_value(node, source.get("comments_selector"), source.get("comments_attr"))
        )

        raw_metadata = {
            "list_url": source["list_url"],
            "source_name": source.get("name"),
            "source_label": source.get("source_label", source.get("name")),
            "detail_fetched": False,
        }

        if source.get("detail_body_selector") or source.get("detail_title_selector") or source.get("detail_author_selector") or source.get("detail_date_selector") or source.get("detail_community_selector"):
            try:
                detail_html = self._get_text(detail_url, headers={**base_headers, **source.get("request_headers", {})})
                detail_doc = parse_html_document(detail_html)
                raw_metadata["detail_fetched"] = True
                title = compact_whitespace(
                    self._node_text(self._select_node(detail_doc, source.get("detail_title_selector"))) or title
                )
                body = self._node_text(self._select_node(detail_doc, source.get("detail_body_selector"))) or body
                author = self._node_text(self._select_node(detail_doc, source.get("detail_author_selector"))) or author
                community = (
                    compact_whitespace(self._node_text(self._select_node(detail_doc, source.get("detail_community_selector"))))
                    or community
                )
                detail_date_value = self._node_value(detail_doc, source.get("detail_date_selector"), source.get("detail_date_attr"))
                if detail_date_value:
                    created_at = self._safe_datetime(detail_date_value)
            except Exception as exc:
                logger.warning("HTML detail fetch failed for %s: %s", detail_url, exc)
                raw_metadata["detail_error"] = str(exc)

        return self.normalizer.normalize(
            source=self.source_name,
            ingestion_method="html_generic",
            community=community,
            source_item_id=f"{source.get('name', 'html')}:html:{make_short_hash(detail_url, title)}",
            url=detail_url,
            title=title,
            body=body,
            author=author,
            created_at=created_at,
            score=None,
            comments_count=comments_count,
            raw_metadata=raw_metadata,
            content_type=source.get("content_type", "thread"),
            parent_source_item_id=None,
            ingestion_run_id=run_id,
        )

    def _node_value(self, root: HtmlNode, selectors: str | list[str] | None, attr_name: str | None) -> str | None:
        node = self._select_node(root, selectors)
        if not node:
            return None
        if attr_name:
            return self._node_attr(node, attr_name)
        return self._node_text(node)

    def _node_text(self, node: HtmlNode | None) -> str:
        if not node:
            return ""
        return compact_whitespace(node.text_content())

    def _node_attr(self, node: HtmlNode | None, attr_name: str) -> str | None:
        if not node:
            return None
        return node.attrs.get(attr_name.lower())

    def _select_node(self, root: HtmlNode, selectors: str | list[str] | None) -> HtmlNode | None:
        if not selectors:
            return None
        selector_list = selectors if isinstance(selectors, list) else [selectors]
        for selector in selector_list:
            node = select_first(root, selector)
            if node:
                return node
        return None

    def _select_nodes(self, root: HtmlNode, selectors: str | list[str]) -> list[HtmlNode]:
        selector_list = selectors if isinstance(selectors, list) else [selectors]
        for selector in selector_list:
            nodes = select_all(root, selector)
            if nodes:
                return nodes
        return []

    def _get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        response = self.session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.text

    def _parse_integer(self, value: str | None) -> int | None:
        if not value:
            return None
        match = INTEGER_RE.search(value.replace(",", ""))
        return int(match.group()) if match else None

    def _safe_datetime(self, value: str | None):
        if not value:
            return utc_now()
        try:
            return parse_discourse_datetime(value)
        except Exception:
            return utc_now()
