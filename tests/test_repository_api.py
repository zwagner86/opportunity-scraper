from __future__ import annotations

import yaml


def test_dedupe_and_candidate_query_filters(db_conn, seed_item):
    from app.repositories.items import ItemRepository

    first_id = seed_item(
        source_item_id="a1",
        title="Wish there was an easier meal plan app",
        body="As a parent, I manually track grocery planning in a spreadsheet every week and there has to be a better way.",
    )
    second_id = seed_item(
        source="stack_exchange",
        community="household_budgeting",
        source_item_id="a2",
        title="Budgeting for groceries keeps getting messy",
        body="I hate dealing with grocery budgeting, I copy and paste numbers every week, and I keep track of subscriptions in a sheet.",
    )
    comment_id = seed_item(
        source_item_id="a1:comment:1",
        title="Comment on: Wish there was an easier meal plan app",
        body="We do this with a shared note and it is still a mess.",
        content_type="comment",
        url="https://example.com/a1#comment-1",
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

    total, items = repo.query_items({"source": "stack_exchange", "limit": 10, "offset": 0, "sort_by": "overall_score"})
    assert total == 1
    assert items[0]["id"] == second_id

    total, items = repo.query_items({"candidate_only": False, "content_role": "supporting_comment", "limit": 10, "offset": 0, "sort_by": "overall_score"})
    assert total >= 1
    assert any(item["id"] == comment_id for item in items)

    total, items = repo.query_items({"candidate_only": False, "include_supporting": True, "limit": 10, "offset": 0, "sort_by": "overall_score"})
    assert total >= 3


def test_api_item_update_and_candidate_defaults(client, seed_item):
    item_id = seed_item(
        source_item_id="api-1",
        title="There has to be a better way to coordinate wedding vendors",
        body="I keep copying timelines between docs and spreadsheets and follow up with everyone manually.",
    )
    seed_item(
        source_item_id="api-1:comment:1",
        title="Comment on: There has to be a better way to coordinate wedding vendors",
        body="We do the same thing with a shared note.",
        content_type="comment",
        url="https://example.com/api-1#comment-1",
    )

    items_response = client.get("/api/items")
    assert items_response.status_code == 200
    ids = {item["id"] for item in items_response.json()["items"]}
    assert item_id in ids
    assert all(item["is_candidate"] is True for item in items_response.json()["items"])

    expanded_response = client.get("/api/items", params={"candidate_only": False, "include_supporting": True})
    assert expanded_response.status_code == 200
    assert expanded_response.json()["total"] >= items_response.json()["total"]

    patch_response = client.patch(f"/api/items/{item_id}", json={"saved": True, "notes": "top candidate"})
    assert patch_response.status_code == 200
    assert patch_response.json()["saved"] is True
    assert patch_response.json()["notes"] == "top candidate"

    stats_response = client.get("/api/stats")
    assert stats_response.status_code == 200
    assert stats_response.json()["candidate_items"] >= 1
    assert stats_response.json()["saved_items"] >= 1


def test_manual_reddit_import_endpoint_marks_comments_as_supporting_or_background(client):
    payload = {
        "threads": [
            {
                "url": "https://www.reddit.com/r/parenting/comments/example/thread_slug/",
                "community": "parenting",
                "title": "Wish there was a better way to manage school pickup",
                "body": "I manually update a spreadsheet and text everyone because school pickup is always changing.",
                "comments": [
                    {
                        "body": "We do the same with a shared note and it is still messy."
                    }
                ],
            }
        ]
    }

    response = client.post("/api/imports/reddit-manual", json=payload)
    assert response.status_code == 200
    assert response.json()["new_item_count"] == 2

    duplicate_response = client.post("/api/imports/reddit-manual", json=payload)
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["duplicate_count"] >= 1

    items_response = client.get("/api/items", params={"source": "reddit", "ingestion_method": "manual_reddit_url"})
    assert items_response.status_code == 200
    assert items_response.json()["total"] == 1
    assert items_response.json()["items"][0]["content_role"] == "primary_candidate"

    expanded_response = client.get(
        "/api/items",
        params={"source": "reddit", "ingestion_method": "manual_reddit_url", "candidate_only": False, "include_supporting": True},
    )
    assert expanded_response.status_code == 200
    assert expanded_response.json()["total"] >= 2

    detail_response = client.get(f"/api/items/{items_response.json()['items'][0]['id']}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["supporting_items"]) >= 1


def test_default_source_pack_is_everyday_life_focused():
    with open("configs/sources.yaml", "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    assert config["enabled_sources"] == ["html_generic", "stack_exchange"]
    assert config["html_generic"]["enabled"] is True
    assert config["hacker_news"]["enabled"] is False
    assert config["discourse"]["enabled"] is False
    communities = [query["community"] for query in config["stack_exchange"]["queries"]]
    assert "parenting_family_logistics" in communities
    assert "household_budgeting" in communities
    assert "travel_coordination" in communities
    html_source_names = [source["name"] for source in config["html_generic"]["sources"]]
    assert "mse_consumer_rights" in html_source_names
    assert "mse_praise_vent_warnings" in html_source_names
    assert "mse_debt_free_wannabe" in html_source_names
    assert "mse_marriage_relationships_families" in html_source_names
    assert "mse_overseas_holidays_travel_planning" in html_source_names
