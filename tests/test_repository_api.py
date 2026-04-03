from __future__ import annotations


def test_dedupe_and_query_filters(db_conn, seed_item):
    from app.repositories.items import ItemRepository
    from app.analysis.opportunity import OpportunityAnalyzer
    from app.repositories.runs import RunRepository
    from app.services.normalizer import Normalizer
    from app.utils.text import utc_now

    first_id = seed_item(
        source_item_id="a1",
        title="Wish there was an easier meal plan app",
        body="As a parent, I manually track grocery planning in a spreadsheet every week.",
    )
    second_id = seed_item(
        source="hacker_news",
        community="ask",
        source_item_id="a2",
        title="Freelancers need a better client follow-up tool",
        body="How do you handle repetitive proposal follow-ups without copy and paste?",
    )

    repo = ItemRepository(db_conn)
    assert repo.has_duplicate_hash(repo.get_item(first_id)["dedupe_hash"], "discourse", "elsewhere") is True

    repo.update_item(first_id, {"saved": True, "notes": "strong niche"})
    total, items = repo.query_items({"saved_only": True, "limit": 10, "offset": 0, "sort_by": "overall_score"})
    assert total == 1
    assert items[0]["id"] == first_id

    total, items = repo.query_items({"tag": "parents", "limit": 10, "offset": 0, "sort_by": "overall_score"})
    assert total == 1
    assert items[0]["id"] == first_id

    total, items = repo.query_items({"source": "hacker_news", "limit": 10, "offset": 0, "sort_by": "overall_score"})
    assert total == 1
    assert items[0]["id"] == second_id


def test_api_item_update_and_stats(client, seed_item):
    item_id = seed_item(
        source_item_id="api-1",
        title="There has to be a better way to coordinate wedding vendors",
        body="I keep copying timelines between docs and spreadsheets.",
    )

    items_response = client.get("/api/items")
    assert items_response.status_code == 200
    assert items_response.json()["total"] >= 1

    patch_response = client.patch(f"/api/items/{item_id}", json={"saved": True, "notes": "top candidate"})
    assert patch_response.status_code == 200
    assert patch_response.json()["saved"] is True
    assert patch_response.json()["notes"] == "top candidate"

    stats_response = client.get("/api/stats")
    assert stats_response.status_code == 200
    assert stats_response.json()["saved_items"] >= 1
