# Architecture

Opportunity Finder is organized as three local services:

- `api`: FastAPI service that owns ingestion, normalization, analysis, clustering, exports, and SQLite persistence
- `dashboard`: Streamlit UI that talks to the API over HTTP
- `n8n`: manual and optional scheduled orchestration that triggers API workflows

Pipeline shape:

1. Automated adapters fetch raw items from public sources such as selector-driven HTML discussion pages, Stack Exchange, and optional RSS, Hacker News, or Discourse feeds when you enable them.
2. A manual Reddit intake flow lets the user import selected Reddit thread URLs with manually supplied thread/comment content.
3. The normalizer converts every source into a shared item model, tags each record with an `ingestion_method`, and computes a stable dedupe hash.
4. The opportunity analyzer captures pain-point evidence, assigns taxonomy tags and likely solution types, computes transparent score components, and classifies each item as a `primary_candidate`, `supporting_comment`, or `background` row.
5. The repository persists items, evidence, scores, tags, clusters, and ingestion runs into SQLite and updates FTS indexes.
6. The clustering service groups related primary candidates using TF-IDF plus cosine similarity.
7. The dashboard reads the API for candidate-first overview metrics, search/filter results, manual Reddit intake, detail inspection, supporting evidence, and exports.

The v1 architecture is intentionally rules-first. It keeps the model inspectable now while leaving room to layer in embeddings or BERTopic later without reshaping the database or public API. Reddit remains a first-class analytical source, but in this version it enters the system only through manual imports rather than automated fetching. The current default source pack is also intentionally narrow so the product optimizes for relevance over raw volume, and the HTML adapter is designed for public server-rendered sources before any browser automation is considered. The default HTML set now targets complaint-heavy consumer boards rather than broad technical communities.
