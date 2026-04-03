from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections import defaultdict
from typing import Any

from app.models.domain import AnalysisResult, NormalizedItem


SORT_FIELDS = {
    "created_at": "items.created_at DESC",
    "overall_score": "item_scores.overall_opportunity_score DESC",
    "source_score": "items.score DESC",
}


class ItemRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert_item(self, item: NormalizedItem, analysis: AnalysisResult) -> tuple[int, bool]:
        existing = self.conn.execute(
            "SELECT id FROM items WHERE source = ? AND source_item_id = ?",
            (item.source, item.source_item_id),
        ).fetchone()
        if existing:
            item_id = int(existing["id"])
            self.conn.execute(
                """
                UPDATE items
                SET community = ?,
                    url = ?,
                    title = ?,
                    body = ?,
                    author = ?,
                    created_at = ?,
                    score = ?,
                    comments_count = ?,
                    raw_metadata_json = ?,
                    content_type = ?,
                    parent_source_item_id = ?,
                    ingestion_run_id = ?,
                    ingested_at = ?,
                    dedupe_hash = ?,
                    language_signals_json = ?,
                    solution_types_json = ?,
                    is_self_serve_friendly = ?,
                    spam_score = ?
                WHERE id = ?
                """,
                (
                    item.community,
                    item.url,
                    item.title,
                    item.body,
                    item.author,
                    item.created_at.isoformat(),
                    item.score,
                    item.comments_count,
                    json.dumps(item.raw_metadata),
                    item.content_type,
                    item.parent_source_item_id,
                    item.ingestion_run_id,
                    item.ingested_at.isoformat(),
                    item.dedupe_hash,
                    json.dumps(item.language_signals),
                    json.dumps(analysis.solution_types),
                    int(analysis.is_self_serve_friendly),
                    analysis.spam_score,
                    item_id,
                ),
            )
            self._replace_analysis(item_id, analysis)
            return item_id, False

        cursor = self.conn.execute(
            """
            INSERT INTO items (
                source,
                community,
                source_item_id,
                url,
                title,
                body,
                author,
                created_at,
                score,
                comments_count,
                raw_metadata_json,
                content_type,
                parent_source_item_id,
                ingestion_run_id,
                ingested_at,
                dedupe_hash,
                language_signals_json,
                solution_types_json,
                is_self_serve_friendly,
                spam_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.source,
                item.community,
                item.source_item_id,
                item.url,
                item.title,
                item.body,
                item.author,
                item.created_at.isoformat(),
                item.score,
                item.comments_count,
                json.dumps(item.raw_metadata),
                item.content_type,
                item.parent_source_item_id,
                item.ingestion_run_id,
                item.ingested_at.isoformat(),
                item.dedupe_hash,
                json.dumps(item.language_signals),
                json.dumps(analysis.solution_types),
                int(analysis.is_self_serve_friendly),
                analysis.spam_score,
            ),
        )
        item_id = int(cursor.lastrowid)
        self._replace_analysis(item_id, analysis)
        return item_id, True

    def has_duplicate_hash(self, dedupe_hash: str, source: str, source_item_id: str) -> bool:
        row = self.conn.execute(
            """
            SELECT id
            FROM items
            WHERE dedupe_hash = ?
              AND NOT (source = ? AND source_item_id = ?)
            LIMIT 1
            """,
            (dedupe_hash, source, source_item_id),
        ).fetchone()
        return row is not None

    def _replace_analysis(self, item_id: int, analysis: AnalysisResult) -> None:
        self.conn.execute("DELETE FROM item_evidence WHERE item_id = ?", (item_id,))
        self.conn.execute("DELETE FROM item_scores WHERE item_id = ?", (item_id,))
        self.conn.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))

        for evidence in analysis.evidence:
            self.conn.execute(
                """
                INSERT INTO item_evidence (item_id, category, signal, phrase, snippet, weight)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    evidence.category,
                    evidence.signal,
                    evidence.phrase,
                    evidence.snippet,
                    evidence.weight,
                ),
            )

        self.conn.execute(
            """
            INSERT INTO item_scores (
                item_id,
                pain_intensity_score,
                repetition_score,
                workaround_score,
                self_serve_score,
                build_simplicity_score,
                sales_friction_penalty,
                competition_signal_score,
                overall_opportunity_score,
                rationale_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                analysis.scores.pain_intensity_score,
                analysis.scores.repetition_score,
                analysis.scores.workaround_score,
                analysis.scores.self_serve_score,
                analysis.scores.build_simplicity_score,
                analysis.scores.sales_friction_penalty,
                analysis.scores.competition_signal_score,
                analysis.scores.overall_opportunity_score,
                json.dumps(analysis.scores.rationale),
            ),
        )

        for tag in analysis.tags:
            self.conn.execute(
                "INSERT OR IGNORE INTO tags (name, tag_type) VALUES (?, ?)",
                (tag.name, tag.tag_type),
            )
            tag_row = self.conn.execute(
                "SELECT id FROM tags WHERE name = ? AND tag_type = ?",
                (tag.name, tag.tag_type),
            ).fetchone()
            self.conn.execute(
                "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
                (item_id, int(tag_row["id"])),
            )

    def update_item(self, item_id: int, payload: dict[str, Any]) -> None:
        fields = []
        params = []
        for field in ("saved", "dismissed", "notes"):
            if field in payload:
                fields.append(f"{field} = ?")
                value = payload[field]
                if field in {"saved", "dismissed"}:
                    value = int(bool(value))
                params.append(value)
        if not fields:
            return
        params.append(item_id)
        self.conn.execute(
            f"UPDATE items SET {', '.join(fields)} WHERE id = ?",
            tuple(params),
        )

    def get_item(self, item_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT items.*,
                   item_scores.pain_intensity_score,
                   item_scores.repetition_score,
                   item_scores.workaround_score,
                   item_scores.self_serve_score,
                   item_scores.build_simplicity_score,
                   item_scores.sales_friction_penalty,
                   item_scores.competition_signal_score,
                   item_scores.overall_opportunity_score,
                   item_scores.rationale_json,
                   clusters.label AS cluster_label,
                   clusters.description AS cluster_description
            FROM items
            LEFT JOIN item_scores ON item_scores.item_id = items.id
            LEFT JOIN clusters ON clusters.id = items.cluster_id
            WHERE items.id = ?
            """,
            (item_id,),
        ).fetchone()
        if not row:
            return None
        item = self._deserialize_item(row)
        item["evidence"] = [
            dict(evidence)
            for evidence in self.conn.execute(
                """
                SELECT category, signal, phrase, snippet, weight
                FROM item_evidence
                WHERE item_id = ?
                ORDER BY weight DESC, id ASC
                """,
                (item_id,),
            ).fetchall()
        ]
        item["tags"] = [
            dict(tag)
            for tag in self.conn.execute(
                """
                SELECT tags.name, tags.tag_type
                FROM item_tags
                JOIN tags ON tags.id = item_tags.tag_id
                WHERE item_tags.item_id = ?
                ORDER BY tags.tag_type, tags.name
                """,
                (item_id,),
            ).fetchall()
        ]
        return item

    def query_items(self, filters: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        joins = ["LEFT JOIN item_scores ON item_scores.item_id = items.id"]
        where = ["1 = 1"]
        params: list[Any] = []

        if q := filters.get("query"):
            joins.append("JOIN items_fts ON items_fts.rowid = items.id")
            where.append("items_fts MATCH ?")
            params.append(q)
        if keyword := filters.get("keyword"):
            where.append("(items.title LIKE ? OR items.body LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if source := filters.get("source"):
            where.append("items.source = ?")
            params.append(source)
        if community := filters.get("community"):
            where.append("items.community = ?")
            params.append(community)
        if start_date := filters.get("start_date"):
            where.append("items.created_at >= ?")
            params.append(start_date)
        if end_date := filters.get("end_date"):
            where.append("items.created_at <= ?")
            params.append(end_date)
        if min_score := filters.get("min_score"):
            where.append("item_scores.overall_opportunity_score >= ?")
            params.append(min_score)
        if filters.get("self_serve_only"):
            where.append("items.is_self_serve_friendly = 1")
        if filters.get("saved_only"):
            where.append("items.saved = 1")
        if filters.get("dismissed_only"):
            where.append("items.dismissed = 1")
        if solution_type := filters.get("solution_type"):
            where.append("EXISTS (SELECT 1 FROM json_each(items.solution_types_json) WHERE value = ?)")
            params.append(solution_type)
        if tag_name := filters.get("tag"):
            joins.append("JOIN item_tags ON item_tags.item_id = items.id")
            joins.append("JOIN tags ON tags.id = item_tags.tag_id")
            where.append("tags.name = ?")
            params.append(tag_name)
        if tag_type := filters.get("tag_type"):
            joins.append("JOIN item_tags AS filter_item_tags ON filter_item_tags.item_id = items.id")
            joins.append("JOIN tags AS filter_tags ON filter_tags.id = filter_item_tags.tag_id")
            where.append("filter_tags.tag_type = ?")
            params.append(tag_type)

        joins_sql = " ".join(dict.fromkeys(joins))
        where_sql = " AND ".join(where)
        count_row = self.conn.execute(
            f"SELECT COUNT(DISTINCT items.id) AS total FROM items {joins_sql} WHERE {where_sql}",
            tuple(params),
        ).fetchone()

        sort = SORT_FIELDS.get(filters.get("sort_by", "overall_score"), SORT_FIELDS["overall_score"])
        limit = int(filters.get("limit", 50))
        offset = int(filters.get("offset", 0))
        rows = self.conn.execute(
            f"""
            SELECT DISTINCT items.*,
                   item_scores.overall_opportunity_score,
                   item_scores.pain_intensity_score,
                   item_scores.repetition_score,
                   item_scores.workaround_score,
                   item_scores.self_serve_score,
                   item_scores.build_simplicity_score,
                   item_scores.sales_friction_penalty,
                   item_scores.competition_signal_score,
                   clusters.label AS cluster_label
            FROM items
            {joins_sql}
            LEFT JOIN clusters ON clusters.id = items.cluster_id
            WHERE {where_sql}
            ORDER BY {sort}
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        ).fetchall()
        items = [self._deserialize_item(row) for row in rows]
        return int(count_row["total"]), items

    def list_clusters(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, label, description, key_terms_json, item_count, avg_score
            FROM clusters
            ORDER BY avg_score DESC, item_count DESC, label ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                **dict(row),
                "key_terms": json.loads(row["key_terms_json"]),
            }
            for row in rows
        ]

    def get_cluster(self, cluster_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM clusters WHERE id = ?",
            (cluster_id,),
        ).fetchone()
        if not row:
            return None
        cluster = dict(row)
        cluster["key_terms"] = json.loads(cluster.pop("key_terms_json"))
        cluster["items"] = []
        item_rows = self.conn.execute(
            """
            SELECT items.*,
                   item_scores.overall_opportunity_score,
                   cluster_items.similarity_score
            FROM cluster_items
            JOIN items ON items.id = cluster_items.item_id
            LEFT JOIN item_scores ON item_scores.item_id = items.id
            WHERE cluster_items.cluster_id = ?
            ORDER BY item_scores.overall_opportunity_score DESC, similarity_score DESC
            """,
            (cluster_id,),
        ).fetchall()
        cluster["items"] = [self._deserialize_item(item) for item in item_rows]
        return cluster

    def replace_clusters(self, clusters: list[dict[str, Any]]) -> None:
        self.conn.execute("UPDATE items SET cluster_id = NULL")
        self.conn.execute("DELETE FROM cluster_items")
        self.conn.execute("DELETE FROM clusters")
        for cluster in clusters:
            cursor = self.conn.execute(
                """
                INSERT INTO clusters (label, description, key_terms_json, item_count, avg_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster["label"],
                    cluster.get("description"),
                    json.dumps(cluster.get("key_terms", [])),
                    len(cluster.get("items", [])),
                    cluster.get("avg_score"),
                    cluster["created_at"],
                    cluster["updated_at"],
                ),
            )
            cluster_id = int(cursor.lastrowid)
            for member in cluster.get("items", []):
                self.conn.execute(
                    """
                    INSERT INTO cluster_items (cluster_id, item_id, similarity_score)
                    VALUES (?, ?, ?)
                    """,
                    (cluster_id, member["item_id"], member["similarity_score"]),
                )
                self.conn.execute(
                    "UPDATE items SET cluster_id = ? WHERE id = ?",
                    (cluster_id, member["item_id"]),
                )

    def get_items_for_analysis(self, limit: int = 1000) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT items.*,
                   item_scores.overall_opportunity_score
            FROM items
            LEFT JOIN item_scores ON item_scores.item_id = items.id
            WHERE items.dismissed = 0
            ORDER BY item_scores.overall_opportunity_score DESC, items.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._deserialize_item(row) for row in rows]

    def list_recent_items(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT items.*,
                   item_scores.overall_opportunity_score
            FROM items
            LEFT JOIN item_scores ON item_scores.item_id = items.id
            ORDER BY items.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._deserialize_item(row) for row in rows]

    def get_stats(self) -> dict[str, Any]:
        totals = self.conn.execute(
            """
            SELECT COUNT(*) AS total_items,
                   SUM(saved) AS saved_items,
                   SUM(dismissed) AS dismissed_items,
                   AVG(item_scores.overall_opportunity_score) AS avg_score
            FROM items
            LEFT JOIN item_scores ON item_scores.item_id = items.id
            """
        ).fetchone()
        stats = dict(totals)
        stats["saved_items"] = int(stats.get("saved_items") or 0)
        stats["dismissed_items"] = int(stats.get("dismissed_items") or 0)
        for key, tag_type in (
            ("top_audiences", "audience"),
            ("top_problem_types", "problem_type"),
        ):
            stats[key] = [
                dict(row)
                for row in self.conn.execute(
                    """
                    SELECT tags.name, COUNT(*) AS count
                    FROM item_tags
                    JOIN tags ON tags.id = item_tags.tag_id
                    WHERE tags.tag_type = ?
                    GROUP BY tags.name
                    ORDER BY count DESC, tags.name ASC
                    LIMIT 10
                    """,
                    (tag_type,),
                ).fetchall()
            ]
        stats["top_sources"] = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT source AS name, COUNT(*) AS count
                FROM items
                GROUP BY source
                ORDER BY count DESC, source ASC
                """
            ).fetchall()
        ]
        stats["top_communities"] = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT community AS name, COUNT(*) AS count
                FROM items
                GROUP BY community
                ORDER BY count DESC, community ASC
                LIMIT 10
                """
            ).fetchall()
        ]
        stats["score_distribution"] = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT CAST(item_scores.overall_opportunity_score AS INTEGER) AS bucket,
                       COUNT(*) AS count
                FROM item_scores
                GROUP BY bucket
                ORDER BY bucket
                """
            ).fetchall()
        ]
        return stats

    def export_items(self, filters: dict[str, Any], fmt: str) -> str:
        _, items = self.query_items({**filters, "limit": filters.get("limit", 500), "offset": 0})
        if fmt == "markdown":
            lines = ["# Opportunity Finder Export", ""]
            for item in items:
                lines.append(f"## {item['title'] or '(untitled)'}")
                lines.append(f"- Source: {item['source']} / {item['community']}")
                lines.append(f"- Score: {item.get('overall_opportunity_score', 0):.2f}")
                lines.append(f"- URL: {item['url']}")
                body = (item.get("body") or "").strip()
                if body:
                    lines.append(f"- Summary: {body[:280]}")
                lines.append("")
            return "\n".join(lines)

        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "id",
                "source",
                "community",
                "title",
                "body",
                "url",
                "created_at",
                "overall_opportunity_score",
                "solution_types",
                "saved",
                "dismissed",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "id": item["id"],
                    "source": item["source"],
                    "community": item["community"],
                    "title": item["title"],
                    "body": item["body"],
                    "url": item["url"],
                    "created_at": item["created_at"],
                    "overall_opportunity_score": item.get("overall_opportunity_score"),
                    "solution_types": ", ".join(item.get("solution_types", [])),
                    "saved": item["saved"],
                    "dismissed": item["dismissed"],
                }
            )
        return buffer.getvalue()

    def _deserialize_item(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for field in (
            "raw_metadata_json",
            "language_signals_json",
            "solution_types_json",
            "rationale_json",
        ):
            if field in item and item[field] is not None:
                item[field] = json.loads(item[field])
        item["raw_metadata"] = item.pop("raw_metadata_json", {})
        item["language_signals"] = item.pop("language_signals_json", [])
        item["solution_types"] = item.pop("solution_types_json", [])
        if "rationale_json" in item:
            item["rationale"] = item.pop("rationale_json")
        item["saved"] = bool(item.get("saved"))
        item["dismissed"] = bool(item.get("dismissed"))
        return item
