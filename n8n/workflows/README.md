# n8n Workflows

These workflows are designed to run inside the `n8n` container from `docker-compose.yml`.

Import these JSON files from the n8n UI:

1. Open `http://localhost:5678`
2. Create or sign in to your local n8n workspace
3. Choose `Import from File`
4. Import any workflow from this directory

Available workflows:

- `opportunity_finder_all_sources.json`: runs ingestion for all enabled sources, including any configured public HTML boards, then refreshes candidate clusters and generates a markdown summary
- `opportunity_finder_hacker_news.json`: runs Hacker News-only ingestion if you explicitly enable that source
- `opportunity_finder_discourse.json`: runs Discourse-only ingestion if you explicitly enable that source
- `opportunity_finder_cluster_refresh.json`: recomputes topic clusters
- `opportunity_finder_markdown_summary.json`: generates a markdown summary from top-ranked results

Manual Reddit imports are handled through the dashboard and `POST /api/imports/reddit-manual`, not n8n automation. The default product posture is candidate-first and household-oriented, so many teams will only need the all-sources workflow plus occasional manual Reddit imports.

Normalization, scoring, tagging, dedupe, and persistence all happen inside the FastAPI backend during ingestion. The workflows intentionally stay thin and orchestrate the backend over HTTP.
