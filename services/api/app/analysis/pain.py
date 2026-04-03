from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.config.loader import AppConfig
from app.models.domain import EvidenceRecord, NormalizedItem
from app.utils.text import compact_whitespace


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_'-]{2,}")
STOPWORDS = {
    "about",
    "again",
    "being",
    "there",
    "their",
    "which",
    "would",
    "could",
    "should",
    "thing",
    "things",
    "because",
    "really",
    "still",
    "while",
    "where",
    "every",
    "doing",
    "using",
    "need",
    "want",
    "with",
    "that",
    "this",
    "from",
    "have",
    "into",
    "over",
    "when",
    "your",
}


class PainSignalDetector:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def detect(self, item: NormalizedItem, related_items: list[dict[str, Any]]) -> tuple[list[EvidenceRecord], dict[str, float]]:
        text = f"{item.title}\n{item.body}".lower()
        evidence: list[EvidenceRecord] = []
        counts = Counter()
        positive_signals = {
            "frustration",
            "manual_work",
            "search_for_tool",
            "recurring_admin",
            "coordination_pain",
            "self_serve",
        }
        negative_signals = {"b2b_penalty", "technical_penalty", "support_penalty"}
        soft_signals = {"generic_question", "advice_request"}

        for signal_name, phrases in self.config.keywords.pain_signals.items():
            for phrase in phrases:
                if phrase.lower() in text:
                    counts[signal_name] += 1
                    evidence.append(
                        EvidenceRecord(
                            category=self._category(signal_name, positive_signals, negative_signals, soft_signals),
                            signal=signal_name,
                            phrase=phrase,
                            snippet=self._snippet(text, phrase),
                            weight=self._weight(signal_name),
                        )
                    )

        if any(
            phrase in text
            for phrase in (
                "i built my own",
                "my own spreadsheet",
                "my own system",
                "my own checklist",
                "i ended up making a sheet",
                "i made a spreadsheet",
            )
        ):
            counts["manual_work"] += 1
            evidence.append(
                EvidenceRecord(
                    category="pain_signal",
                    signal="manual_work",
                    phrase="built my own system",
                    snippet=self._snippet(text, "my own"),
                    weight=2.0,
                )
            )

        similar_count = self._similar_count(item, related_items)
        if similar_count:
            counts["repetition"] += similar_count
            evidence.append(
                EvidenceRecord(
                    category="theme_repetition",
                    signal="cross_thread_similarity",
                    phrase=f"{similar_count} similar items",
                    snippet="Repeated theme found across separate items with overlapping keywords.",
                    weight=min(3.0, 1.0 + similar_count * 0.5),
                )
            )

        strong_pain = (
            counts["frustration"]
            + counts["manual_work"]
            + counts["search_for_tool"]
            + counts["recurring_admin"]
            + counts["coordination_pain"]
        )

        if item.comments_count and item.comments_count >= 8 and strong_pain:
            counts["comment_density"] += 1
            evidence.append(
                EvidenceRecord(
                    category="engagement_signal",
                    signal="complaint_density",
                    phrase=f"{item.comments_count} comments",
                    snippet="High engagement around a pain-heavy discussion.",
                    weight=1.2,
                )
            )

        return evidence, {
            "frustration": float(counts["frustration"]),
            "manual_work": float(counts["manual_work"]),
            "search_for_tool": float(counts["search_for_tool"]),
            "recurring_admin": float(counts["recurring_admin"]),
            "coordination_pain": float(counts["coordination_pain"]),
            "self_serve": float(counts["self_serve"]),
            "b2b_penalty": float(counts["b2b_penalty"]),
            "technical_penalty": float(counts["technical_penalty"]),
            "support_penalty": float(counts["support_penalty"]),
            "generic_question": float(counts["generic_question"]),
            "advice_request": float(counts["advice_request"]),
            "repetition": float(counts["repetition"]),
            "comment_density": float(counts["comment_density"]),
            "strong_pain": float(strong_pain),
            "soft_context": float(counts["generic_question"] + counts["advice_request"]),
        }

    def spam_score(self, item: NormalizedItem) -> float:
        text = f"{item.title}\n{item.body}".lower()
        return float(sum(1 for phrase in self.config.keywords.spam_signals if phrase.lower() in text))

    def _similar_count(self, item: NormalizedItem, related_items: list[dict[str, Any]]) -> int:
        base_terms = set(self._keywords(f"{item.title} {item.body}"))
        if not base_terms:
            return 0
        matches = 0
        for other in related_items:
            other_terms = set(self._keywords(f"{other.get('title', '')} {other.get('body', '')}"))
            if len(base_terms.intersection(other_terms)) >= 3:
                matches += 1
        return matches

    def _keywords(self, text: str) -> list[str]:
        tokens = [token.lower() for token in TOKEN_RE.findall(text)]
        return [token for token in tokens if token not in STOPWORDS]

    def _snippet(self, text: str, phrase: str) -> str:
        lower_phrase = phrase.lower()
        index = text.find(lower_phrase)
        if index == -1:
            return compact_whitespace(text[:180])
        start = max(0, index - 60)
        end = min(len(text), index + len(lower_phrase) + 100)
        return compact_whitespace(text[start:end])

    def _weight(self, signal_name: str) -> float:
        mapping = {
            "frustration": 2.1,
            "manual_work": 1.9,
            "search_for_tool": 1.6,
            "recurring_admin": 1.8,
            "coordination_pain": 1.8,
            "self_serve": 1.2,
            "b2b_penalty": 2.1,
            "technical_penalty": 2.0,
            "support_penalty": 1.6,
            "generic_question": 0.8,
            "advice_request": 0.8,
        }
        return mapping.get(signal_name, 1.0)

    def _category(
        self,
        signal_name: str,
        positive_signals: set[str],
        negative_signals: set[str],
        soft_signals: set[str],
    ) -> str:
        if signal_name in positive_signals:
            return "pain_signal"
        if signal_name in negative_signals:
            return "relevance_penalty"
        if signal_name in soft_signals:
            return "context_signal"
        return "pain_signal"
