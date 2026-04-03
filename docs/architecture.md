# Architecture

Opportunity Finder is organized as three local services:

- `api`: FastAPI service that owns ingestion, normalization, analysis, clustering, exports, and SQLite persistence
- `dashboard`: Streamlit UI that talks to the API over HTTP
- `n8n`: manual and optional scheduled orchestration that triggers API workflows

Pipeline shape:

1. Source adapters fetch raw items from Reddit, Hacker News, and Discourse.
2. The normalizer converts them into a shared item model and computes a stable dedupe hash.
3. The opportunity analyzer captures pain-point evidence, assigns taxonomy tags and likely solution types, and computes transparent score components.
4. The repository persists items, evidence, scores, tags, and ingestion runs into SQLite and updates FTS indexes.
5. The clustering service groups related opportunities using TF-IDF plus cosine similarity.
6. The dashboard reads the API for overview metrics, search/filter results, detail inspection, and exports.

The v1 architecture is intentionally rules-first. It keeps the model inspectable now while leaving room to layer in embeddings or BERTopic later without reshaping the database or public API.

