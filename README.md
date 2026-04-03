# Opportunity Finder v1

Opportunity Finder is a local-first application for discovering product and service opportunities from Reddit, Hacker News, and selected Discourse communities. It pulls public discussions, normalizes them into a shared local dataset, detects pain points and unmet needs, scores them transparently, clusters related themes, and provides a Streamlit dashboard for browsing and curation.

The project is built to be free, self-hosted, and maintainable. v1 uses rules and heuristics instead of paid APIs or speculative ML layers, with a code layout that makes future upgrades straightforward.

## Stack

- `FastAPI` for ingestion, scoring, clustering, exports, and API endpoints
- `SQLite` for local persistence with FTS5 search
- `Streamlit` for the dashboard
- `n8n` for manual and optional scheduled orchestration
- `Docker Compose` for local setup

## Repository layout

- `configs/`: editable source, scoring, keyword, and taxonomy config
- `docker/`: Dockerfiles for the API and dashboard
- `docs/`: architecture notes
- `n8n/workflows/`: importable workflow JSON files
- `services/api/`: backend service and SQLite migrations
- `services/dashboard/`: Streamlit dashboard
- `services/shared/`: shared helpers space for future cross-service code
- `tests/`: core logic and API tests

## What v1 does

- Ingests from:
  - Reddit via PRAW
  - Hacker News public API
  - Discourse JSON endpoints, with RSS fallback
- Normalizes content into a shared schema
- Stores evidence for matched pain signals
- Scores opportunities with explicit component scores:
  - `pain_intensity_score`
  - `repetition_score`
  - `workaround_score`
  - `self_serve_score`
  - `build_simplicity_score`
  - `sales_friction_penalty`
  - `competition_signal_score`
  - `overall_opportunity_score`
- Assigns audience tags, problem-type tags, and likely solution types
- Supports SQLite FTS5 search and practical filters
- Clusters related items into lightweight topical groups
- Lets you save, dismiss, and annotate opportunities in the dashboard
- Exports filtered results to CSV and Markdown

## Environment variables

Copy `.env.example` to `.env` and edit as needed.

Core settings:

- `OPPORTUNITY_DB_PATH`: SQLite database path
- `OPPORTUNITY_CONFIG_DIR`: config directory path
- `OPPORTUNITY_API_BASE_URL`: dashboard API base URL

Reddit settings:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

## Reddit API credentials

1. Visit `https://www.reddit.com/prefs/apps`
2. Click `create another app...`
3. Choose `script`
4. Give it a name like `opportunity-finder-local`
5. Set the redirect URI to `http://localhost:8080`
6. Copy the client ID and secret into `.env`
7. Set a descriptive user agent such as `opportunity-finder/1.0 by YOUR_REDDIT_USERNAME`

## Local setup with Docker Compose

1. Copy `.env.example` to `.env`
2. Update Reddit credentials if you want Reddit ingestion enabled
3. Review `configs/sources.yaml` and adjust target communities or fetch limits
4. Start the stack:

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`
- n8n: `http://localhost:5678`

## Running ingestion

### From the dashboard

- Open `http://localhost:8501`
- Use the `Run ingestion now` button on the overview page

### From the API directly

Run all enabled sources:

```bash
curl -X POST http://localhost:8000/api/runs/ingest \
  -H "Content-Type: application/json" \
  -d '{"sources": null}'
```

Run a specific source:

```bash
curl -X POST http://localhost:8000/api/runs/ingest \
  -H "Content-Type: application/json" \
  -d '{"sources": ["reddit"]}'
```

Refresh clusters:

```bash
curl -X POST http://localhost:8000/api/clusters/refresh \
  -H "Content-Type: application/json" \
  -d '{}'
```

Generate a markdown summary:

```bash
curl -X POST http://localhost:8000/api/summaries/markdown \
  -H "Content-Type: application/json" \
  -d '{"limit": 20, "min_score": 5.5}'
```

## Dashboard usage

The dashboard has three main views:

- `Overview`: top-level metrics, recent runs, source/community charts, score distribution, and quick actions
- `Results`: full-text search, filters, sortable table, detail inspection, evidence, score breakdown, save/dismiss, notes, and export
- `Clusters`: browse topic groups built from similar language and tags

## n8n setup

The included workflows orchestrate the backend over HTTP rather than reimplementing pipeline logic inside n8n.

1. Open `http://localhost:5678`
2. Import one or more JSON files from `n8n/workflows/`
3. Run them manually, or add your own schedule node later

Included workflows:

- `opportunity_finder_all_sources.json`
- `opportunity_finder_reddit.json`
- `opportunity_finder_hacker_news.json`
- `opportunity_finder_discourse.json`
- `opportunity_finder_cluster_refresh.json`
- `opportunity_finder_markdown_summary.json`

Normalization, scoring, dedupe, and persistence all happen in the backend during ingestion.

## Config files

Editable YAML files live in `configs/`:

- `sources.yaml`: enabled sources, communities, forums, fetch limits, ignored communities
- `scoring.yaml`: scoring weights and thresholds
- `keywords.yaml`: pain, self-serve, spam, and B2B signal keywords
- `taxonomy.yaml`: audience, problem-type, and likely solution-type definitions

## SQLite schema

The API applies numbered SQL migrations automatically on startup from `services/api/migrations/`.

Key tables:

- `items`
- `ingestion_runs`
- `item_evidence`
- `item_scores`
- `tags`
- `item_tags`
- `clusters`
- `cluster_items`
- `items_fts`

## Adding a new adapter

1. Create a new adapter in `services/api/app/adapters/` implementing `SourceAdapter.fetch`
2. Normalize fetched content through `services/api/app/services/normalizer.py`
3. Register the adapter in `services/api/app/services/ingestion.py`
4. Add source config to `configs/sources.yaml`
5. Add tests for normalization and ingestion behavior

The rest of the pipeline should not need to change if the adapter outputs the shared normalized model.

## Running tests

Tests live under `tests/` and focus on core logic rather than UI snapshots.

When dependencies are installed:

```bash
PYTHONPATH=services/api pytest tests
```

## Limitations in v1

- Scoring and tagging are heuristic and rules-first
- Clustering is lightweight TF-IDF similarity, not embeddings or BERTopic
- Reddit ingestion depends on local API credentials
- Discourse support assumes public JSON or RSS endpoints
- Browser automation is intentionally excluded
- There is no background job worker beyond n8n orchestration and manual API runs

## Future improvements

- Add embeddings-based recall and semantic clustering
- Add more public forum adapters
- Improve spam filtering and cross-source similarity dedupe
- Add richer charts and saved search presets
- Add scheduled workflows and digest delivery

