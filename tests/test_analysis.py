from __future__ import annotations


def test_scoring_prefers_consumer_self_serve_opportunity(configured_env):
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    analyzer = OpportunityAnalyzer()
    normalizer = Normalizer()

    consumer_item = normalizer.normalize(
        source="reddit",
        community="parents",
        source_item_id="consumer-1",
        url="https://example.com/consumer-1",
        title="Wish there was an app for school pickup coordination",
        body="I manually update a spreadsheet every day and there has to be a better way.",
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

    assert consumer.scores.overall_opportunity_score > b2b.scores.overall_opportunity_score
    assert consumer.is_self_serve_friendly is True
    assert b2b.scores.sales_friction_penalty > consumer.scores.sales_friction_penalty


def test_taxonomy_and_solution_assignment(configured_env):
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    item = Normalizer().normalize(
        source="reddit",
        community="creators",
        source_item_id="creator-1",
        url="https://example.com/creator-1",
        title="Creators need a better content calendar and budgeting template",
        body="I track newsletter planning and compare sponsors in a spreadsheet.",
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

    assert "creators" in tag_names
    assert "planning" in tag_names
    assert "budgeting" in tag_names
    assert "template_product" in analysis.solution_types

