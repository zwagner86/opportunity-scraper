# Opportunity Finder v1

Opportunity Finder is a local-first application for discovering product and service opportunities from public communities. It is now tuned for everyday-life complaints first: household logistics, family coordination, budgeting, pets, travel planning, and similar consumer pain points. It supports manual Reddit imports for curated high-signal threads and automated discovery from public non-Reddit sources, including public HTML discussion boards that do not expose formal APIs.

The backend normalizes everything into one local SQLite dataset, applies rules-first pain-point detection, scores opportunities transparently, clusters related themes, and exposes the results in a Streamlit dashboard.

## Stack

- `FastAPI` for ingestion, manual imports, scoring, clustering, exports, and API endpoints
- `SQLite` for local persistence with FTS5 search
- `Streamlit` for the dashboard
- `n8n` for manual and optional scheduled orchestration
- `Docker Compose` for local setup

## What v1 does

- Automated ingestion from public sources such as:
  - generic public HTML discussion pages via config-driven selectors
  - Stack Exchange public API
  - generic RSS/Atom feeds
  - optional Hacker News and Discourse adapters when you explicitly enable them
- Manual Reddit imports from selected Reddit thread URLs plus user-supplied thread/comment content
- Candidate-first relevance gating so explicit complaints and workaround-heavy threads rise while generic questions and technical chatter mostly fall out
- Shared normalization, tagging, scoring, clustering, save/dismiss, notes, and exports across all sources
- Source-aware filtering plus `ingestion_method`, `candidate_only`, and `content_role` filtering so you can distinguish primary candidates from supporting evidence

## Repository layout

- `configs/`: editable source, scoring, keyword, and taxonomy config
- `docker/`: Dockerfiles for the API and dashboard
- `docs/`: architecture notes
- `n8n/workflows/`: importable workflow JSON files
- `services/api/`: backend service and SQLite migrations
- `services/dashboard/`: Streamlit dashboard
- `services/shared/`: shared helpers space for future cross-service code
- `tests/`: core logic and API tests

## Environment variables

Copy `.env.example` to `.env` and edit as needed.

- `OPPORTUNITY_DB_PATH`: SQLite database path
- `OPPORTUNITY_CONFIG_DIR`: config directory path
- `OPPORTUNITY_API_BASE_URL`: dashboard API base URL

No Reddit credentials are required in this version because Reddit is manual-import only.

## Local setup with Docker Compose

1. Copy `.env.example` to `.env`
2. Review `configs/sources.yaml`. The default starter pack is intentionally narrow and household-focused, with public HTML sources enabled alongside a small Stack Exchange pack.
   The HTML pack now leans on complaint-heavy MoneySavingExpert boards such as consumer rights, praise/vent threads, debt pressure, family logistics, home problems, and travel planning.
3. Start the stack:

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`
- n8n: `http://localhost:5678`

## Running automated ingestion

### From the dashboard

- Open `http://localhost:8501`
- Use the `Run ingestion now` button on the overview page

### From the API directly

Run all enabled automated sources:

```bash
curl -X POST http://localhost:8000/api/runs/ingest \
  -H "Content-Type: application/json" \
  -d '{"sources": null}'
```

Run a specific automated source:

```bash
curl -X POST http://localhost:8000/api/runs/ingest \
  -H "Content-Type: application/json" \
  -d '{"sources": ["stack_exchange"]}'
```

Run only the HTML source pack:

```bash
curl -X POST http://localhost:8000/api/runs/ingest \
  -H "Content-Type: application/json" \
  -d '{"sources": ["html_generic"]}'
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

## Manual Reddit import

Use the dashboard page `Manual Reddit Import` for the easiest flow.

Workflow:

1. Paste one or more Reddit thread URLs
2. Fill in the thread title, body, and community manually
3. Optionally paste only the top comments that strengthen the thread-level pain point
4. Preview the batch
5. Import it into the same scoring pipeline as the automated sources

API endpoints:

- `GET /api/imports/reddit-template`
- `POST /api/imports/reddit-manual`

Example payload:

```json
{
  "threads": [
    {
      "url": "https://www.reddit.com/r/parenting/comments/example/thread_slug/",
      "community": "parenting",
      "title": "Wish there was a better way to manage school pickup",
      "body": "I manually update a spreadsheet and text everyone.",
      "comments": [
        {
          "body": "We do this with a shared note and it is still messy."
        }
      ]
    }
  ]
}
```

## Dashboard usage

The dashboard has four main views:

- `Overview`: candidate-focused metrics, recent runs, source/community charts, score distribution, and quick actions
- `Results`: candidate-first search, filters, sortable table, detail inspection, supporting evidence, score breakdown, save/dismiss, notes, and export
- `Clusters`: browse topic groups built from similar language and tags
- `Manual Reddit Import`: URL-first manual intake for Reddit threads and comments

The results page opens in an `Everyday-life candidates` mode by default:

- primary candidate threads only
- supporting comments hidden unless you opt in
- low-signal technical/support items suppressed from the default view

## n8n setup

The included workflows orchestrate automated public-source ingestion over HTTP rather than reimplementing pipeline logic inside n8n.

1. Open `http://localhost:5678`
2. Import one or more JSON files from `n8n/workflows/`
3. Run them manually, or add your own schedule node later

Included workflows:

- `opportunity_finder_all_sources.json`
- `opportunity_finder_hacker_news.json`
- `opportunity_finder_discourse.json`
- `opportunity_finder_cluster_refresh.json`
- `opportunity_finder_markdown_summary.json`

Manual Reddit imports are performed from the dashboard or via `POST /api/imports/reddit-manual`, not n8n automation.

## Config files

Editable YAML files live in `configs/`:

- `sources.yaml`: enabled automated sources, everyday-life Stack Exchange presets, optional RSS feeds, optional Discourse/Hacker News adapters, and manual Reddit defaults
  - includes `html_generic`, a config-driven adapter for public server-rendered discussion pages
- `scoring.yaml`: scoring weights and thresholds
- `keywords.yaml`: complaint, workaround, recurring-admin, technical penalty, spam, and B2B signal keywords
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

Each item also stores an `ingestion_method`, `is_candidate`, `candidate_reason`, and `content_role` so manual Reddit imports and automated sources remain comparable while still distinguishing primary opportunities from supporting evidence.

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
- Reddit is manual-import only in this version
- The default starter pack is intentionally narrow and precision-oriented, so total volume may be lower than broader discovery tools
- Generic HTML sources depend on stable public page structure and may need selector tuning over time
- Generic RSS feeds vary in metadata quality
- Discourse and Hacker News remain supported in code, but they are disabled in the default starter pack because they tend to produce more technical or low-signal material
- Browser automation and login-backed Reddit intake are intentionally excluded
- There is no background job worker beyond n8n orchestration and manual API runs

## Future improvements

- Add embeddings-based recall and semantic clustering
- Add richer feed templates and additional public-source adapters
- Improve spam filtering and cross-source similarity dedupe
- Add saved search presets and richer charting
- Add manual import helpers for pasted markdown or uploaded files
