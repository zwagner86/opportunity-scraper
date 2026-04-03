from __future__ import annotations

import pandas as pd
import streamlit as st

from app.api_client import APIClient
from app.ui import render_distribution_chart, render_metric_card, setup_page


setup_page("Overview")
client = APIClient()

st.title("Opportunity Finder")
st.caption("Local-first discovery for recurring consumer, prosumer, hobbyist, and local-service pain points.")

top_bar = st.columns([1.2, 1, 1, 1])
with top_bar[0]:
    if st.button("Run ingestion now", use_container_width=True):
        with st.spinner("Running ingestion across enabled sources..."):
            response = client.post("/runs/ingest", {"sources": None})
        st.session_state["last_run_response"] = response
        st.success(response["summary"])
with top_bar[1]:
    if st.button("Refresh clusters", use_container_width=True):
        response = client.post("/clusters/refresh", {})
        st.success(f"Refreshed {response['clusters_created']} clusters.")
with top_bar[2]:
    if st.button("Generate markdown summary", use_container_width=True):
        summary = client.post("/summaries/markdown", {"limit": 15, "min_score": 5.5})
        st.session_state["latest_markdown_summary"] = summary["markdown"]
with top_bar[3]:
    st.page_link("pages/1_Results.py", label="Open results")

stats = client.get("/stats")
runs = client.get("/runs", limit=12)

metric_cols = st.columns(4)
with metric_cols[0]:
    render_metric_card("Total items", str(stats.get("total_items", 0)), "All normalized items in local SQLite")
with metric_cols[1]:
    render_metric_card("Saved", str(stats.get("saved_items", 0)), "High-interest opportunities you marked")
with metric_cols[2]:
    avg_score = stats.get("avg_score") or 0
    render_metric_card("Average score", f"{avg_score:.2f}", "Across all scored opportunities")
with metric_cols[3]:
    render_metric_card("Dismissed", str(stats.get("dismissed_items", 0)), "Items hidden from the main hunt")

chart_cols = st.columns(2)
with chart_cols[0]:
    render_distribution_chart("Top Niches", stats.get("top_audiences", []), "name", "count")
with chart_cols[1]:
    render_distribution_chart("Top Problem Types", stats.get("top_problem_types", []), "name", "count")

chart_cols = st.columns(2)
with chart_cols[0]:
    render_distribution_chart("Top Sources", stats.get("top_sources", []), "name", "count")
with chart_cols[1]:
    render_distribution_chart("Top Communities", stats.get("top_communities", []), "name", "count")

render_distribution_chart("Score Distribution", stats.get("score_distribution", []), "bucket", "count")

st.subheader("Recent runs")
runs_df = pd.DataFrame(runs)
if runs_df.empty:
    st.info("No ingestion runs yet. Use the button above to pull from the configured sources.")
else:
    display_df = runs_df[["id", "status", "started_at", "finished_at", "item_count", "new_item_count", "duplicate_count", "error_count", "summary"]]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

if st.session_state.get("latest_markdown_summary"):
    st.subheader("Latest markdown summary")
    st.code(st.session_state["latest_markdown_summary"], language="markdown")
