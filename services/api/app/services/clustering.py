from __future__ import annotations

import sqlite3
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.repositories.items import ItemRepository
from app.utils.text import utc_now


class ClusterService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.items = ItemRepository(conn)

    def refresh(self) -> dict[str, Any]:
        items = self.items.get_items_for_analysis(limit=1000)
        if len(items) < 2:
            self.items.replace_clusters([])
            return {"status": "completed", "clusters_created": 0}

        docs = []
        for item in items:
            docs.append(
                " ".join(
                    [
                        item.get("title", ""),
                        item.get("body", ""),
                        " ".join(item.get("solution_types", [])),
                    ]
                )
            )

        vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
        matrix = vectorizer.fit_transform(docs)
        similarity = cosine_similarity(matrix)
        terms = vectorizer.get_feature_names_out()
        clusters: list[dict[str, Any]] = []
        visited: set[int] = set()
        timestamp = utc_now().isoformat()

        for idx, item in enumerate(items):
            if idx in visited:
                continue
            member_indexes = [candidate for candidate, score in enumerate(similarity[idx]) if score >= 0.18]
            if len(member_indexes) < 2:
                continue
            for member in member_indexes:
                visited.add(member)
            centroid = matrix[member_indexes].mean(axis=0).A1
            ranked = centroid.argsort()[::-1][:5]
            key_terms = [terms[position] for position in ranked if centroid[position] > 0]
            label = ", ".join(key_terms[:3]) if key_terms else item.get("community", "misc")
            avg_score = sum((items[index].get("overall_opportunity_score") or 0) for index in member_indexes) / len(member_indexes)
            clusters.append(
                {
                    "label": label.title(),
                    "description": f"Grouped from similar language and tags around {label}.",
                    "key_terms": key_terms,
                    "avg_score": round(avg_score, 2),
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "items": [
                        {
                            "item_id": items[member]["id"],
                            "similarity_score": round(float(similarity[idx][member]), 3),
                        }
                        for member in member_indexes
                    ],
                }
            )

        self.items.replace_clusters(clusters)
        return {"status": "completed", "clusters_created": len(clusters)}
