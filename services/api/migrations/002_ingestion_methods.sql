ALTER TABLE ingestion_runs ADD COLUMN ingestion_method TEXT NOT NULL DEFAULT 'mixed';

ALTER TABLE items ADD COLUMN ingestion_method TEXT NOT NULL DEFAULT 'legacy';

UPDATE items
SET ingestion_method = CASE
    WHEN source = 'hacker_news' THEN 'api_hacker_news'
    WHEN source = 'discourse' THEN 'json_discourse'
    WHEN source = 'stack_exchange' THEN 'api_stackexchange'
    WHEN source = 'rss_generic' THEN 'rss_generic'
    WHEN source = 'reddit' THEN 'manual_reddit_url'
    ELSE 'legacy'
END
WHERE ingestion_method = 'legacy';

UPDATE ingestion_runs
SET ingestion_method = CASE
    WHEN sources_json = '["reddit"]' THEN 'manual_reddit_url'
    WHEN sources_json = '["hacker_news"]' THEN 'api_hacker_news'
    WHEN sources_json = '["discourse"]' THEN 'json_discourse'
    WHEN sources_json = '["stack_exchange"]' THEN 'api_stackexchange'
    WHEN sources_json = '["rss_generic"]' THEN 'rss_generic'
    ELSE 'mixed'
END
WHERE ingestion_method = 'mixed';
