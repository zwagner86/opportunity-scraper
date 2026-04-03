from __future__ import annotations

import pandas as pd
import streamlit as st

from app.api_client import APIClient
from app.ui import filter_sidebar, render_badges, render_score_breakdown, setup_page


setup_page("Results")
client = APIClient()
filters = filter_sidebar("results")

st.title("Results")
st.caption("Search, rank, inspect evidence, and curate promising opportunities.")

items_response = client.get("/items", **filters)
items = items_response.get("items", [])
total = items_response.get("total", 0)

action_cols = st.columns([1, 1, 2])
with action_cols[0]:
    csv_export = client.get_text("/export", format="csv", **filters)
    st.download_button("Export CSV", csv_export, file_name="opportunities.csv", use_container_width=True)
with action_cols[1]:
    markdown_export = client.get_text("/export", format="markdown", **filters)
    st.download_button("Export Markdown", markdown_export, file_name="opportunities.md", use_container_width=True)
with action_cols[2]:
    st.markdown(f"**{total}** matching items")

if not items:
    st.info("No items match the current filters yet.")
    st.stop()

table_df = pd.DataFrame(
    [
        {
            "id": item["id"],
            "source": item["source"],
            "community": item["community"],
            "title": item["title"][:90],
            "score": item.get("overall_opportunity_score"),
            "self_serve": item.get("is_self_serve_friendly"),
            "saved": item.get("saved"),
            "dismissed": item.get("dismissed"),
        }
        for item in items
    ]
)
st.dataframe(table_df, use_container_width=True, hide_index=True)

selected_id = st.selectbox(
    "Inspect item",
    options=[item["id"] for item in items],
    format_func=lambda item_id: next(
        f"{item['title'][:85]} | {item['community']} | {item.get('overall_opportunity_score', 0):.2f}"
        for item in items
        if item["id"] == item_id
    ),
)

detail = client.get(f"/items/{selected_id}")

detail_cols = st.columns([1.4, 1])
with detail_cols[0]:
    st.subheader(detail.get("title") or "(untitled)")
    st.caption(f"{detail['source']} / {detail['community']} | {detail['content_type']} | {detail['created_at']}")
    st.markdown(f"[Open source item]({detail['url']})")
    if detail.get("body"):
        st.write(detail["body"])
    else:
        st.caption("No body content available for this item.")

    st.markdown("**Audience tags**")
    render_badges([tag["name"] for tag in detail.get("tags", []) if tag["tag_type"] == "audience"])
    st.markdown("**Problem-type tags**")
    render_badges(
        [tag["name"] for tag in detail.get("tags", []) if tag["tag_type"] == "problem_type"],
        "badge-problem",
    )
    st.markdown("**Likely solution types**")
    render_badges(detail.get("solution_types", []), "badge-solution")

    st.markdown("**Evidence**")
    evidence = detail.get("evidence", [])
    if not evidence:
        st.caption("No evidence captured for this item yet.")
    for signal in evidence:
        st.markdown(
            f"""
            <div class="panel-card" style="margin-bottom:0.65rem;">
                <div style="font-weight:700;">{signal['signal']}</div>
                <div class="muted">{signal['phrase']}</div>
                <div style="margin-top:0.35rem;">{signal['snippet']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with detail_cols[1]:
    st.metric("Opportunity score", f"{detail.get('overall_opportunity_score', 0):.2f}")
    render_score_breakdown(detail)

    with st.form("item_actions"):
        saved = st.checkbox("Saved", value=detail.get("saved", False))
        dismissed = st.checkbox("Dismissed", value=detail.get("dismissed", False))
        notes = st.text_area("Notes", value=detail.get("notes", ""), height=180)
        submitted = st.form_submit_button("Update item", use_container_width=True)
        if submitted:
            client.patch(f"/items/{selected_id}", {"saved": saved, "dismissed": dismissed, "notes": notes})
            st.success("Item updated.")

    if detail.get("raw_metadata"):
        st.markdown("**Source metadata**")
        st.json(detail["raw_metadata"])
