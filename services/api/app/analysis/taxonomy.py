from __future__ import annotations

from app.config.loader import AppConfig
from app.models.domain import NormalizedItem, TagAssignment


class TaxonomyTagger:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def assign(self, item: NormalizedItem) -> list[TagAssignment]:
        text = f"{item.title}\n{item.body}".lower()
        tags: list[TagAssignment] = []
        tags.extend(self._match_group(text, self.config.taxonomy.audiences, "audience"))
        tags.extend(self._match_group(text, self.config.taxonomy.problem_types, "problem_type"))
        return tags

    def assign_solution_types(self, item: NormalizedItem) -> list[str]:
        text = f"{item.title}\n{item.body}".lower()
        matches = [
            name
            for name, keywords in self.config.taxonomy.solution_types.items()
            if any(keyword.lower() in text for keyword in keywords)
        ]
        if any(keyword in text for keyword in ("hire", "contractor", "find someone", "local service")):
            matches.extend(["marketplace", "service_business"])
        if any(keyword in text for keyword in ("spreadsheet", "template", "checklist")):
            matches.append("template_product")
        if any(keyword in text for keyword in ("calendar", "reminder", "habit", "schedule")):
            matches.extend(["mobile_app", "simple_web_app"])
        if any(keyword in text for keyword in ("automate", "integration", "copy and paste")):
            matches.append("workflow_automation")

        deduped: list[str] = []
        for value in matches:
            if value not in deduped:
                deduped.append(value)
        return deduped

    def _match_group(self, text: str, mapping: dict[str, list[str]], tag_type: str) -> list[TagAssignment]:
        results = []
        for name, keywords in mapping.items():
            if any(keyword.lower() in text for keyword in keywords):
                results.append(TagAssignment(name=name, tag_type=tag_type))
        return results

