from __future__ import annotations

import pandas as pd
import streamlit as st

from app.api_client import APIClient
from app.ui import (
    filter_sidebar,
    format_content_role,
    format_ingestion_method,
    format_source_name,
    render_badges,
    render_score_breakdown,
    setup_page,
)


setup_page("Results")
client = APIClient()
filters = filter_sidebar("results")


def inclusion_reasons(detail: dict[str, object]) -> list[str]:
    evidence = detail.get("evidence", []) or []
    reasons: list[str] = []
    signals = {signal["signal"] for signal in evidence if isinstance(signal, dict)}
    if "frustration" in signals:
        reasons.append("Explicit complaint language")
    if "manual_work" in signals:
        reasons.append("Manual workaround behavior")
    if {"recurring_admin", "coordination_pain"}.intersection(signals):
        reasons.append("Recurring life-admin or coordination friction")
    if "cross_thread_similarity" in signals:
        reasons.append("Theme repeated across multiple items")
    return reasons


st.title("Results")
st.caption("Candidate-first results for everyday-life pains, with supporting comments available only when you choose to include them.")

items_response = client.get("/items", **filters)
items = items_response.get("items", [])
total = items_response.get("total", 0)

active_filter_count = sum(
    1
    for key, value in filters.items()
    if value not in (None, "", False, 0) and key not in {"limit", "sort_by", "candidate_only"}
)

summary_cols = st.columns(4)
with summary_cols[0]:
    st.metric("Matching rows", total)
with summary_cols[1]:
    st.metric("Mode", "Candidates only" if filters.get("candidate_only", True) and not filters.get("include_supporting") else "Expanded view")
with summary_cols[2]:
    st.metric("Active filters", active_filter_count)
with summary_cols[3]:
    st.metric("Rows loaded", len(items))

st.markdown(
    """
    <div class="hero-card">
        <div class="section-label">Preset</div>
        <div style="font-size:1rem;line-height:1.6;color:#314240;">
            The default view hides low-signal chatter. You can widen the lens with <strong>Include supporting comments</strong> in the sidebar when you want extra context.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

action_cols = st.columns([1, 1, 2])
with action_cols[0]:
    csv_export = client.get_text("/export", format="csv", **filters)
    st.download_button("Export CSV", csv_export, file_name="opportunities.csv", use_container_width=True)
with action_cols[1]:
    markdown_export = client.get_text("/export", format="markdown", **filters)
    st.download_button("Export Markdown", markdown_export, file_name="opportunities.md", use_container_width=True)
with action_cols[2]:
    st.caption("Scan the short list, then inspect a candidate below to see why it passed the gate.")

if not items:
    st.info("No items match the current candidate view yet. Try manual Reddit import, relax a filter, or disable candidate-only mode in the sidebar.")
    st.stop()

table_df = pd.DataFrame(
    [
        {
            "id": item["id"],
            "status": format_content_role(item.get("content_role")),
            "source": format_source_name(item["source"]),
            "community": item["community"],
            "title": item["title"][:88],
            "score": round(item.get("overall_opportunity_score") or 0, 2),
            "reason": (item.get("candidate_reason") or "")[:80],
            "saved": "Saved" if item.get("saved") else "",
        }
        for item in items
    ]
)
st.subheader("Opportunity list")
st.dataframe(table_df, use_container_width=True, hide_index=True)

selected_id = st.selectbox(
    "Inspect item",
    options=[item["id"] for item in items],
    format_func=lambda item_id: next(
        f"{item['title'][:80]} | {format_content_role(item.get('content_role'))} | {item.get('overall_opportunity_score', 0):.2f}"
        for item in items
        if item["id"] == item_id
    ),
)

detail = client.get(f"/items/{selected_id}")
why_included = inclusion_reasons(detail)

detail_cols = st.columns([1.55, 1])
with detail_cols[0]:
    st.subheader(detail.get("title") or "(untitled)")
    st.caption(
        f"{format_content_role(detail.get('content_role'))} | "
        f"{format_source_name(detail['source'])} / {detail['community']} | "
        f"{format_ingestion_method(detail.get('ingestion_method'))} | "
        f"{detail['content_type']} | {detail['created_at']}"
    )
    st.markdown(
        f"""
        <div class="panel-card" style="margin-bottom:0.9rem;">
            <div class="section-label">Why This Was Included</div>
            <div style="font-weight:700;margin-bottom:0.35rem;">{detail.get("candidate_reason") or "No candidate summary available."}</div>
            <div class="muted">{' | '.join(why_included) if why_included else 'No strong inclusion reasons were derived from the current evidence set.'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"[Open source item]({detail['url']})")
    if detail.get("parent_item"):
        parent = detail["parent_item"]
        st.info(f"Supporting item for: {parent.get('title') or '(untitled parent thread)'}")
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

    if detail.get("supporting_items"):
        st.markdown("**Supporting comments**")
        for supporting in detail["supporting_items"]:
            st.markdown(
                f"""
                <div class="panel-card" style="margin-bottom:0.65rem;">
                    <div style="display:flex;justify-content:space-between;gap:1rem;">
                        <div style="font-weight:700;">{supporting.get('author') or 'Anonymous'}</div>
                        <div class="muted">{supporting.get('overall_opportunity_score', 0) or 0:.2f}</div>
                    </div>
                    <div style="margin-top:0.45rem;">{(supporting.get('body') or '')[:280]}</div>
                    <div class="muted" style="margin-top:0.4rem;">{format_content_role(supporting.get('content_role'))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("**Evidence**")
    evidence = detail.get("evidence", [])
    if not evidence:
        st.caption("No evidence captured for this item yet.")
    for signal in evidence:
        st.markdown(
            f"""
            <div class="panel-card" style="margin-bottom:0.65rem;">
                <div style="display:flex;justify-content:space-between;gap:1rem;">
                    <div style="font-weight:700;">{signal['signal']}</div>
                    <div class="muted">{signal['category']}</div>
                </div>
                <div class="muted">{signal['phrase']}</div>
                <div style="margin-top:0.35rem;">{signal['snippet']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with detail_cols[1]:
    st.metric("Status", format_content_role(detail.get("content_role")))
    st.metric("Opportunity score", f"{detail.get('overall_opportunity_score', 0):.2f}")
    st.metric("Self-serve friendly", "Yes" if detail.get("is_self_serve_friendly") else "No")
    render_score_breakdown(detail)

    with st.form("item_actions"):
        saved = st.checkbox("Saved", value=detail.get("saved", False))
        dismissed = st.checkbox("Dismissed", value=detail.get("dismissed", False))
        notes = st.text_area("Notes", value=detail.get("notes", ""), height=180)
        submitted = st.form_submit_button("Update item", use_container_width=True)
        if submitted:
            client.patch(f"/items/{selected_id}", {"saved": saved, "dismissed": dismissed, "notes": notes})
            st.success("Item updated.")

    if detail.get("rationale"):
        st.markdown("**Scoring rationale**")
        for line in detail["rationale"]:
            st.write(f"- {line}")

    if detail.get("raw_metadata"):
        st.markdown("**Source metadata**")
        st.json(detail["raw_metadata"])
