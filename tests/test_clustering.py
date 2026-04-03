from __future__ import annotations


def test_cluster_service_groups_similar_items(db_conn, seed_item):
    from app.repositories.items import ItemRepository
    from app.services.clustering import ClusterService

    meal_a = seed_item(
        source_item_id="cluster-a",
        title="Need a better meal plan and grocery coordination app",
        body="I manually update a spreadsheet for family meals and grocery runs.",
    )
    meal_b = seed_item(
        source_item_id="cluster-b",
        title="Wish there was a grocery planning tool for busy parents",
        body="School pickup and meal prep planning are messy in my spreadsheet.",
    )
    seed_item(
        source_item_id="cluster-c",
        title="Enterprise procurement workflow issue",
        body="Security review and compliance approvals slow every rollout.",
    )

    summary = ClusterService(db_conn).refresh()
    assert summary["clusters_created"] >= 1

    clusters = ItemRepository(db_conn).list_clusters(limit=10)
    assert clusters
    cluster = ItemRepository(db_conn).get_cluster(clusters[0]["id"])
    member_ids = {item["id"] for item in cluster["items"]}
    assert {meal_a, meal_b}.intersection(member_ids)

