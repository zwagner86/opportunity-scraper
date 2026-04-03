from __future__ import annotations


def test_scoring_prefers_household_complaint_over_sales_heavy_b2b(configured_env):
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    analyzer = OpportunityAnalyzer()
    normalizer = Normalizer()

    consumer_item = normalizer.normalize(
        source="reddit",
        ingestion_method="manual_reddit_url",
        community="parents",
        source_item_id="consumer-1",
        url="https://example.com/consumer-1",
        title="Wish there was an app for school pickup coordination",
        body="I hate dealing with pickup changes, I manually update a spreadsheet every day, and there has to be a better way.",
        author="user",
        created_at=utc_now(),
        score=10,
        comments_count=18,
        raw_metadata={},
        content_type="thread",
        parent_source_item_id=None,
        ingestion_run_id=1,
    )
    b2b_item = normalizer.normalize(
        source="reddit",
        ingestion_method="manual_reddit_url",
        community="enterprise",
        source_item_id="b2b-1",
        url="https://example.com/b2b-1",
        title="Need enterprise procurement workflow software",
        body="Our compliance committee and security review make adoption painful across stakeholders.",
        author="user",
        created_at=utc_now(),
        score=10,
        comments_count=4,
        raw_metadata={},
        content_type="thread",
        parent_source_item_id=None,
        ingestion_run_id=1,
    )

    consumer = analyzer.analyze(consumer_item, related_items=[])
    b2b = analyzer.analyze(b2b_item, related_items=[])

    assert consumer.is_candidate is True
    assert consumer.content_role == "primary_candidate"
    assert consumer.scores.overall_opportunity_score > b2b.scores.overall_opportunity_score
    assert consumer.is_self_serve_friendly is True
    assert b2b.is_candidate is False
    assert b2b.scores.sales_friction_penalty > consumer.scores.sales_friction_penalty


def test_generic_technical_question_is_suppressed(configured_env):
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    item = Normalizer().normalize(
        source="stack_exchange",
        ingestion_method="api_stackexchange",
        community="python_help",
        source_item_id="tech-1",
        url="https://example.com/tech-1",
        title="How do I install this package on Python 3.12?",
        body="My code throws a stack trace after the latest version update. Any recommendations for the API setup?",
        author="user",
        created_at=utc_now(),
        score=5,
        comments_count=2,
        raw_metadata={},
        content_type="thread",
        parent_source_item_id=None,
        ingestion_run_id=1,
    )
    analysis = OpportunityAnalyzer().analyze(item, related_items=[])

    assert analysis.is_candidate is False
    assert analysis.content_role == "background"
    assert "technical" in analysis.candidate_reason.lower() or "support" in analysis.candidate_reason.lower()
    assert analysis.scores.overall_opportunity_score <= 4.4


def test_taxonomy_and_solution_assignment(configured_env):
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    item = Normalizer().normalize(
        source="reddit",
        ingestion_method="manual_reddit_url",
        community="mealplanning",
        source_item_id="meal-1",
        url="https://example.com/meal-1",
        title="Need a better meal planning and grocery checklist",
        body="I keep track of recipes and grocery planning in a spreadsheet and always forget what is in the pantry.",
        author="user",
        created_at=utc_now(),
        score=5,
        comments_count=6,
        raw_metadata={},
        content_type="thread",
        parent_source_item_id=None,
        ingestion_run_id=1,
    )
    analysis = OpportunityAnalyzer().analyze(item, related_items=[])
    tag_names = {tag.name for tag in analysis.tags}

    assert "meal_planning" in tag_names
    assert "planning" in tag_names
    assert "organization" in tag_names
    assert "template_product" in analysis.solution_types


def test_comments_default_to_supporting_evidence_unless_extremely_strong(configured_env):
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    analyzer = OpportunityAnalyzer()
    ordinary_comment = Normalizer().normalize(
        source="reddit",
        ingestion_method="manual_reddit_url",
        community="parenting",
        source_item_id="thread-1:comment:1",
        url="https://example.com/comment-1",
        title="Comment on: thread",
        body="We do the same thing here.",
        author="user",
        created_at=utc_now(),
        score=2,
        comments_count=None,
        raw_metadata={},
        content_type="comment",
        parent_source_item_id="thread-1",
        ingestion_run_id=1,
    )
    strong_comment = Normalizer().normalize(
        source="reddit",
        ingestion_method="manual_reddit_url",
        community="parenting",
        source_item_id="thread-2:comment:1",
        url="https://example.com/comment-2",
        title="Comment on: thread",
        body="I hate dealing with school pickup changes. I manually update a spreadsheet, keep track of everyone's schedule, and there has to be a better way.",
        author="user",
        created_at=utc_now(),
        score=12,
        comments_count=None,
        raw_metadata={},
        content_type="comment",
        parent_source_item_id="thread-2",
        ingestion_run_id=1,
    )

    ordinary_analysis = analyzer.analyze(ordinary_comment, related_items=[])
    strong_analysis = analyzer.analyze(strong_comment, related_items=[])

    assert ordinary_analysis.is_candidate is False
    assert ordinary_analysis.content_role == "background"
    assert strong_analysis.is_candidate is True
    assert strong_analysis.content_role == "primary_candidate"
