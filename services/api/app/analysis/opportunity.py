from __future__ import annotations

from typing import Any

from app.analysis.pain import PainSignalDetector
from app.analysis.scoring import OpportunityScorer
from app.analysis.taxonomy import TaxonomyTagger
from app.config.loader import load_app_config
from app.models.domain import AnalysisResult, NormalizedItem, TagAssignment


class OpportunityAnalyzer:
    def __init__(self) -> None:
        self.config = load_app_config()
        self.detector = PainSignalDetector(self.config)
        self.tagger = TaxonomyTagger(self.config)
        self.scorer = OpportunityScorer(self.config)

    def analyze(self, item: NormalizedItem, related_items: list[dict[str, Any]]) -> AnalysisResult:
        evidence, signals = self.detector.detect(item, related_items)
        tags = self.tagger.assign(item)
        solution_types = self.tagger.assign_solution_types(item)
        tags.extend(TagAssignment(name=value, tag_type="solution_type") for value in solution_types)
        text = f"{item.title}\n{item.body}".lower()
        existing_tool_mentions = sum(
            1
            for phrase in ("tool", "app", "software", "alternative", "competitor")
            if phrase in text
        )
        scores = self.scorer.score(
            signals=signals,
            tags=tags,
            solution_types=solution_types,
            existing_tool_mentions=existing_tool_mentions,
        )
        spam_score = self.detector.spam_score(item)
        is_self_serve_friendly = scores.self_serve_score >= 6.0 and scores.sales_friction_penalty <= 3.5
        return AnalysisResult(
            evidence=evidence,
            scores=scores,
            tags=tags,
            solution_types=solution_types,
            spam_score=spam_score,
            is_self_serve_friendly=is_self_serve_friendly,
        )

