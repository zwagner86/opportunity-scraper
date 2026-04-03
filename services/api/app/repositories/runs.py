from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.utils.text import utc_now


class RunRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, sources: list[str], config_snapshot: dict[str, Any]) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO ingestion_runs (
                started_at,
                status,
                sources_json,
                config_snapshot_json
            ) VALUES (?, 'running', ?, ?)
            """,
            (
                utc_now().isoformat(),
                json.dumps(sources),
                json.dumps(config_snapshot),
            ),
        )
        return int(cursor.lastrowid)

    def finish(
        self,
        run_id: int,
        *,
        status: str,
        item_count: int,
        new_item_count: int,
        duplicate_count: int,
        error_count: int,
        summary: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE ingestion_runs
            SET finished_at = ?,
                status = ?,
                item_count = ?,
                new_item_count = ?,
                duplicate_count = ?,
                error_count = ?,
                summary = ?
            WHERE id = ?
            """,
            (
                utc_now().isoformat(),
                status,
                item_count,
                new_item_count,
                duplicate_count,
                error_count,
                summary,
                run_id,
            ),
        )

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM ingestion_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["sources"] = json.loads(item.pop("sources_json"))
            item["config_snapshot"] = json.loads(item.pop("config_snapshot_json"))
            results.append(item)
        return results

