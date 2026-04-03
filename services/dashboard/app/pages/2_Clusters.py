from __future__ import annotations

import pandas as pd
import streamlit as st

from app.api_client import APIClient
from app.ui import render_badges, setup_page


setup_page("Clusters")
client = APIClient()

st.title("Clusters")
st.caption("Browse grouped opportunity themes built from shared language and tag similarity.")

clusters = client.get("/clusters", limit=100)
if not clusters:
    st.info("No clusters available yet. Run ingestion first or refresh clusters from the overview page.")
    st.stop()

cluster_df = pd.DataFrame(
    [
        {
            "id": cluster["id"],
            "label": cluster["label"],
            "item_count": cluster["item_count"],
            "avg_score": cluster.get("avg_score"),
            "key_terms": ", ".join(cluster.get("key_terms", [])),
        }
        for cluster in clusters
    ]
)
st.dataframe(cluster_df, use_container_width=True, hide_index=True)

cluster_id = st.selectbox(
    "Inspect cluster",
    options=[cluster["id"] for cluster in clusters],
    format_func=lambda value: next(
        f"{cluster['label']} ({cluster['item_count']} items)"
        for cluster in clusters
        if cluster["id"] == value
    ),
)
cluster = client.get(f"/clusters/{cluster_id}")

header_cols = st.columns([1.4, 1])
with header_cols[0]:
    st.subheader(cluster["label"])
    if cluster.get("description"):
        st.write(cluster["description"])
    render_badges(cluster.get("key_terms", []))
with header_cols[1]:
    st.metric("Items in cluster", cluster.get("item_count", 0))
    st.metric("Average score", f"{cluster.get('avg_score', 0) or 0:.2f}")

st.markdown("### Member opportunities")
for item in cluster.get("items", []):
    with st.container():
        st.markdown(
            f"""
            <div class="panel-card" style="margin-bottom:0.8rem;">
                <div style="display:flex;justify-content:space-between;gap:1rem;">
                    <div>
                        <div style="font-weight:700;font-size:1.05rem;">{item['title'] or '(untitled)'}</div>
                        <div class="muted">{item['source']} / {item['community']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div><strong>{item.get('overall_opportunity_score', 0):.2f}</strong></div>
                        <div class="muted">similarity {item.get('similarity_score', 0):.3f}</div>
                    </div>
                </div>
                <div style="margin-top:0.5rem;">{(item.get('body') or '')[:240]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"[Open source item]({item['url']})")
