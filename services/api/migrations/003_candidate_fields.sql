ALTER TABLE items ADD COLUMN is_candidate INTEGER NOT NULL DEFAULT 0;

ALTER TABLE items ADD COLUMN candidate_reason TEXT NOT NULL DEFAULT '';

ALTER TABLE items ADD COLUMN content_role TEXT NOT NULL DEFAULT 'background';

UPDATE items
SET is_candidate = CASE
        WHEN content_type IN ('thread', 'topic', 'story')
         AND COALESCE((SELECT overall_opportunity_score FROM item_scores WHERE item_scores.item_id = items.id), 0) >= 6.5
            THEN 1
        ELSE 0
    END,
    content_role = CASE
        WHEN content_type IN ('comment', 'post') OR parent_source_item_id IS NOT NULL
            THEN 'supporting_comment'
        WHEN content_type IN ('thread', 'topic', 'story')
         AND COALESCE((SELECT overall_opportunity_score FROM item_scores WHERE item_scores.item_id = items.id), 0) >= 6.5
            THEN 'primary_candidate'
        ELSE 'background'
    END,
    candidate_reason = CASE
        WHEN content_type IN ('comment', 'post') OR parent_source_item_id IS NOT NULL
            THEN 'Backfilled supporting item from a prior import. Re-run ingestion to apply the latest relevance rules.'
        WHEN content_type IN ('thread', 'topic', 'story')
         AND COALESCE((SELECT overall_opportunity_score FROM item_scores WHERE item_scores.item_id = items.id), 0) >= 6.5
            THEN 'Backfilled candidate from a prior score. Re-run ingestion to apply the latest relevance rules.'
        ELSE 'Backfilled background item from a prior import. Re-run ingestion to apply the latest relevance rules.'
    END;

CREATE INDEX IF NOT EXISTS idx_items_is_candidate ON items(is_candidate);
CREATE INDEX IF NOT EXISTS idx_items_content_role ON items(content_role);
