from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.items import ItemRepository
from app.utils.text import utc_now


class SummaryService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.items = ItemRepository(conn)

    def generate_markdown(self, limit: int, min_score: float) -> dict[str, Any]:
        _, items = self.items.query_items(
            {
                "limit": limit,
                "offset": 0,
                "sort_by": "overall_score",
                "min_score": min_score,
            }
        )
        lines = ["# Opportunity Summary", ""]
        if not items:
            lines.append("No items matched the requested score threshold.")
        for item in items:
            lines.append(f"## {item['title'] or '(untitled)'}")
            lines.append(f"- Source: {item['source']} / {item['community']}")
            lines.append(f"- Score: {item.get('overall_opportunity_score', 0):.2f}")
            if item.get("solution_types"):
                lines.append(f"- Likely solution types: {', '.join(item['solution_types'])}")
            if item.get("rationale"):
                lines.append(f"- Why it stands out: {' '.join(item['rationale'])}")
            lines.append(f"- URL: {item['url']}")
            lines.append("")
        return {
            "markdown": "\n".join(lines),
            "generated_at": utc_now().isoformat(),
        }
