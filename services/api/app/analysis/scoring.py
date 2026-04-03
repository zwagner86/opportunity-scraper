from __future__ import annotations

from app.config.loader import AppConfig
from app.models.domain import NormalizedItem, ScoreBreakdown, TagAssignment


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

        technical_penalty = signals["technical_penalty"] + signals["support_penalty"]
        soft_context = signals["soft_context"]
        pain_intensity = min(
            10.0,
            max(
                0.0,
                signals["frustration"] * 2.5
                + signals["recurring_admin"] * 1.8
                + signals["coordination_pain"] * 1.7
                + signals["search_for_tool"] * 1.0
                + signals["comment_density"] * 1.1
                - soft_context * 0.35,
            ),
        )
        repetition = min(
            10.0,
            signals["repetition"] * 1.9
            + signals["manual_work"] * 1.4
            + signals["recurring_admin"] * 1.0
            + signals["comment_density"] * 0.8,
        )
        workaround = min(
            10.0,
            signals["manual_work"] * 2.6
            + max(0.0, signals["search_for_tool"] - 0.5)
            + signals["coordination_pain"] * 0.8,
        )

        self_serve = 1.4 + min(2.4, signals["self_serve"] * 1.2)
        if audiences.intersection(consumer_audiences):
            self_serve += 3.5
        if solution_types:
            self_serve += 1.2
        self_serve -= technical_penalty * 1.25
        self_serve -= signals["b2b_penalty"] * 0.75
        self_serve = min(10.0, self_serve)
        self_serve = max(0.0, self_serve)

        build_simplicity = 2.2
        for solution_type in solution_types:
            if solution_type in {"simple_web_app", "mobile_app", "template_product", "workflow_automation", "directory"}:
                build_simplicity += 1.1
            elif solution_type in {"marketplace", "service_business"}:
                build_simplicity += 0.6
            elif solution_type == "micro_saas":
                build_simplicity += 0.9
        if audiences.intersection(consumer_audiences):
            build_simplicity += 0.8
        build_simplicity -= signals["technical_penalty"] * 0.7
        build_simplicity = min(10.0, build_simplicity)
        build_simplicity = max(0.0, build_simplicity)

        sales_penalty = min(10.0, signals["b2b_penalty"] * 2.4)
        competition_signal = min(10.0, existing_tool_mentions * 1.1 + signals["search_for_tool"] * 0.6)

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
            rationale.append("Strong complaint or unmet-need language detected.")
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
        if technical_penalty >= 2:
            rationale.append("Technical or support-heavy framing lowers everyday-user relevance.")

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

    def classify_candidate(
        self,
        *,
        item: NormalizedItem,
        signals: dict[str, float],
        scores: ScoreBreakdown,
    ) -> tuple[bool, str, str]:
        strong_pain = signals["strong_pain"]
        technical_load = signals["technical_penalty"] + signals["support_penalty"]
        soft_context = signals["soft_context"]
        is_supporting_content = item.content_type in {"comment", "post"} or item.parent_source_item_id is not None

        if technical_load >= 2 and strong_pain < 3:
            return False, "Suppressed as low-signal: mostly technical or product-support discussion.", "background"

        if signals["b2b_penalty"] >= 2 and strong_pain < 3:
            return False, "Suppressed as low-signal: enterprise-style adoption friction dominates the problem.", "background"

        if is_supporting_content:
            if strong_pain >= 3 and signals["manual_work"] >= 1 and scores.self_serve_score >= 5.5:
                return True, "Candidate: unusually strong complaint-and-workaround pattern surfaced in a comment.", "primary_candidate"
            if strong_pain >= 1 or signals["repetition"] >= 1:
                return False, "Evidence only: this comment supports a broader thread-level pain point.", "supporting_comment"
            return False, "Suppressed as low-signal: supporting comment without clear unmet-need evidence.", "background"

        has_core_pair = (
            (signals["frustration"] >= 1 and signals["manual_work"] >= 1)
            or (signals["frustration"] >= 1 and signals["search_for_tool"] >= 1)
            or (signals["manual_work"] >= 1 and signals["coordination_pain"] >= 1)
            or (signals["manual_work"] >= 1 and signals["recurring_admin"] >= 1)
        )
        has_repeated_pain = signals["repetition"] >= 1 and strong_pain >= 1
        generic_question_only = soft_context >= 1 and strong_pain < 2 and scores.pain_intensity_score < 4.5

        if has_core_pair or (strong_pain >= 2 and scores.overall_opportunity_score >= 5.2) or has_repeated_pain:
            reasons: list[str] = []
            if signals["frustration"] >= 1:
                reasons.append("explicit complaint")
            if signals["manual_work"] >= 1:
                reasons.append("manual workaround")
            if signals["recurring_admin"] >= 1 or signals["coordination_pain"] >= 1:
                reasons.append("recurring life-admin friction")
            if signals["repetition"] >= 1:
                reasons.append("cross-thread repetition")
            if not reasons:
                reasons.append("clear unmet-need signal")
            summary = ", ".join(reasons[:2])
            return True, f"Candidate: {summary}.", "primary_candidate"

        if generic_question_only:
            return False, "Suppressed as low-signal: asks for advice but lacks a clear recurring pain or workaround.", "background"

        if strong_pain >= 1:
            return False, "Evidence only: some pain is present, but it is not specific enough to stand alone as an opportunity.", "background"

        return False, "Suppressed as low-signal: no explicit complaint, workaround, or recurring life-admin friction detected.", "background"
