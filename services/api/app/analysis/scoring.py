from __future__ import annotations

from app.config.loader import AppConfig
from app.models.domain import ScoreBreakdown, TagAssignment


class OpportunityScorer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def score(
        self,
        *,
        signals: dict[str, float],
        tags: list[TagAssignment],
        solution_types: list[str],
        existing_tool_mentions: int,
    ) -> ScoreBreakdown:
        audiences = {tag.name for tag in tags if tag.tag_type == "audience"}
        consumer_audiences = {
            "parents",
            "pet_owners",
            "homeowners",
            "renters",
            "travelers",
            "creators",
            "gamers",
            "students",
            "freelancers",
            "side_hustles",
            "wedding_planning",
            "fitness",
            "meal_planning",
            "personal_finance",
            "diy_hobbies",
            "mental_wellness",
            "local_community",
            "car_owners",
        }

        pain_intensity = min(10.0, signals["frustration"] * 2.2 + signals["search_for_tool"] * 1.4 + signals["comment_density"] * 1.2)
        repetition = min(10.0, signals["repetition"] * 1.8 + signals["manual_work"] * 1.1)
        workaround = min(10.0, signals["manual_work"] * 2.4 + max(0.0, signals["search_for_tool"] - 1.0))

        self_serve = 2.0 + min(2.5, signals["self_serve"] * 1.4)
        if audiences.intersection(consumer_audiences):
            self_serve += 3.0
        if solution_types:
            self_serve += 1.5
        self_serve = min(10.0, self_serve)

        build_simplicity = 3.0
        for solution_type in solution_types:
            if solution_type in {"simple_web_app", "mobile_app", "template_product", "workflow_automation", "directory"}:
                build_simplicity += 1.1
            elif solution_type in {"marketplace", "service_business"}:
                build_simplicity += 0.6
            elif solution_type == "micro_saas":
                build_simplicity += 0.9
        build_simplicity = min(10.0, build_simplicity)

        sales_penalty = min(10.0, signals["b2b_penalty"] * 2.4)
        competition_signal = min(10.0, existing_tool_mentions * 1.5)

        weights = self.config.scoring.weights
        overall = (
            pain_intensity * weights.get("pain_intensity_score", 1.0)
            + repetition * weights.get("repetition_score", 1.0)
            + workaround * weights.get("workaround_score", 1.0)
            + self_serve * weights.get("self_serve_score", 1.0)
            + build_simplicity * weights.get("build_simplicity_score", 1.0)
            + competition_signal * weights.get("competition_signal_score", 0.5)
            - sales_penalty * weights.get("sales_friction_penalty", 1.0)
        ) / 5.0
        overall = max(0.0, min(10.0, overall))

        rationale = []
        if pain_intensity >= 6:
            rationale.append("Strong frustration or unmet-need language detected.")
        if repetition >= 5:
            rationale.append("Repeated theme or repetitive workflow signals are present.")
        if workaround >= 5:
            rationale.append("Manual workaround behavior suggests product demand.")
        if self_serve >= 6:
            rationale.append("Signals point to self-serve consumer or prosumer adoption.")
        if sales_penalty >= 4:
            rationale.append("Enterprise-style adoption friction lowers attractiveness.")
        if competition_signal >= 3:
            rationale.append("Existing tools are mentioned, suggesting validated demand.")

        return ScoreBreakdown(
            pain_intensity_score=round(pain_intensity, 2),
            repetition_score=round(repetition, 2),
            workaround_score=round(workaround, 2),
            self_serve_score=round(self_serve, 2),
            build_simplicity_score=round(build_simplicity, 2),
            sales_friction_penalty=round(sales_penalty, 2),
            competition_signal_score=round(competition_signal, 2),
            overall_opportunity_score=round(overall, 2),
            rationale=rationale,
        )

