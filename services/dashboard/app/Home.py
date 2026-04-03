from __future__ import annotations

import pandas as pd
import streamlit as st

from app.api_client import APIClient
from app.ui import format_ingestion_method, render_distribution_chart, render_metric_card, setup_page


setup_page("Overview")
client = APIClient()

st.title("Opportunity Finder")
st.caption("Local-first discovery for recurring household, family, neighborhood, and consumer coordination pain points.")
st.markdown(
    """
    <div class="hero-card">
        <div class="section-label">Overview</div>
        <div style="font-size:1.08rem;line-height:1.65;color:#314240;">
            This version is tuned for explicit everyday-life complaints. It prioritizes thread-level problems with visible frustration, manual workarounds, and recurring life-admin friction, while pushing generic questions and technical chatter into the background.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

top_bar = st.columns([1.2, 1, 1, 1, 1.1])
with top_bar[0]:
    if st.button("Run Automated Ingestion", use_container_width=True, type="primary"):
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
    st.page_link("pages/3_Manual_Reddit_Import.py", label="Import Reddit Threads")
with top_bar[4]:
    st.page_link("pages/1_Results.py", label="Open Candidate Results")

stats = client.get("/stats")
runs = client.get("/runs", limit=12)

metric_cols = st.columns(4)
with metric_cols[0]:
    render_metric_card("Candidate threads", str(stats.get("candidate_items", 0)), "Primary opportunities currently shown by default")
with metric_cols[1]:
    render_metric_card("Supporting evidence", str(stats.get("supporting_items", 0)), "Comments and replies stored as evidence, not primary opportunities")
with metric_cols[2]:
    avg_score = stats.get("avg_score") or 0
    render_metric_card("Average candidate score", f"{avg_score:.2f}", "Across candidate items that passed the new gate")
with metric_cols[3]:
    render_metric_card("Saved", str(stats.get("saved_items", 0)), "High-interest opportunities you marked")

chart_cols = st.columns(2)
with chart_cols[0]:
    render_distribution_chart("Top Niches", stats.get("top_audiences", []), "name", "count")
with chart_cols[1]:
    render_distribution_chart("Top Problem Types", stats.get("top_problem_types", []), "name", "count")

chart_cols = st.columns(2)
with chart_cols[0]:
    render_distribution_chart("Top Sources", stats.get("top_sources", []), "name", "count")
with chart_cols[1]:
    render_distribution_chart("Top Ingestion Methods", stats.get("top_ingestion_methods", []), "name", "count")

chart_cols = st.columns(2)
with chart_cols[0]:
    render_distribution_chart("Top Communities", stats.get("top_communities", []), "name", "count")
with chart_cols[1]:
    st.markdown(
        """
        <div class="panel-card">
            <div class="section-label">Manual Intake</div>
            <h3 style="margin-top:0;">Manual Reddit Import</h3>
            <p class="muted">Automated runs now work best with public HTML discussion boards plus a small Stack Exchange pack. Reddit still works best here as a curated thread source when you already know a discussion is rich with real-world pain.</p>
            <p style="margin-bottom:0;"><strong>Best for:</strong> handpicked family, household, budgeting, pets, meal-planning, and local-life threads with real complaint language.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

render_distribution_chart("Score Distribution", stats.get("score_distribution", []), "bucket", "count")

st.subheader("Recent runs")
runs_df = pd.DataFrame(runs)
if runs_df.empty:
    st.info("No ingestion runs yet. Use the button above to pull from the configured sources.")
else:
    runs_df["ingestion_method"] = runs_df["ingestion_method"].map(format_ingestion_method)
    display_df = runs_df[["id", "ingestion_method", "status", "started_at", "finished_at", "item_count", "new_item_count", "duplicate_count", "error_count", "summary"]]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

if st.session_state.get("latest_markdown_summary"):
    st.subheader("Latest markdown summary")
    st.code(st.session_state["latest_markdown_summary"], language="markdown")
