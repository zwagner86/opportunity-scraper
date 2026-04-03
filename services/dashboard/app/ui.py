from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


def setup_page(title: str) -> None:
    st.set_page_config(
        page_title=f"Opportunity Finder | {title}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Instrument+Sans:wght@400;500;600;700&display=swap');
        :root {
            --bg: #f6f2ea;
            --card: #fffdf9;
            --ink: #1f2a2a;
            --accent: #1d6f5f;
            --accent-soft: #d9f0e8;
            --muted: #6e7c78;
            --gold: #d9a441;
            --rose: #c56a5a;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(217, 164, 65, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(29, 111, 95, 0.22), transparent 26%),
                linear-gradient(180deg, #faf7f1 0%, #f2eee5 100%);
            color: var(--ink);
            font-family: "Instrument Sans", sans-serif;
        }
        h1, h2, h3 {
            font-family: "Space Grotesk", sans-serif;
            color: var(--ink);
            letter-spacing: -0.02em;
        }
        .metric-card, .panel-card {
            background: rgba(255, 253, 249, 0.92);
            border: 1px solid rgba(31, 42, 42, 0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 30px rgba(31, 42, 42, 0.06);
        }
        .badge {
            display: inline-block;
            margin: 0.15rem 0.3rem 0.15rem 0;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent);
            font-size: 0.82rem;
            font-weight: 600;
        }
        .badge-problem {
            background: #f3e3cd;
            color: #8a5a11;
        }
        .badge-solution {
            background: #eadff8;
            color: #614189;
        }
        .muted {
            color: var(--muted);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, caption: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="muted">{label}</div>
            <div style="font-size:2rem;font-weight:700;line-height:1.1;">{value}</div>
            <div class="muted" style="font-size:0.9rem;">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badges(values: list[str], badge_class: str = "") -> None:
    if not values:
        st.caption("No tags assigned yet.")
        return
    html = "".join(f'<span class="badge {badge_class}">{value}</span>' for value in values)
    st.markdown(html, unsafe_allow_html=True)


def render_distribution_chart(title: str, data: list[dict[str, Any]], x: str, y: str):
    df = pd.DataFrame(data)
    if df.empty:
        st.info(f"No data available for {title.lower()} yet.")
        return
    figure = px.bar(df, x=x, y=y, title=title, color=y, color_continuous_scale="Tealgrn")
    figure.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.75)",
        coloraxis_showscale=False,
        font=dict(family="Instrument Sans"),
    )
    st.plotly_chart(figure, use_container_width=True)


def render_score_breakdown(item: dict[str, Any]) -> None:
    score_fields = [
        ("Pain", item.get("pain_intensity_score")),
        ("Repetition", item.get("repetition_score")),
        ("Workaround", item.get("workaround_score")),
        ("Self-serve", item.get("self_serve_score")),
        ("Simplicity", item.get("build_simplicity_score")),
        ("Sales penalty", item.get("sales_friction_penalty")),
        ("Competition", item.get("competition_signal_score")),
    ]
    df = pd.DataFrame(
        [{"component": label, "value": value or 0.0} for label, value in score_fields]
    )
    figure = px.bar(
        df,
        x="component",
        y="value",
        color="value",
        color_continuous_scale="Tealgrn",
        title="Score Breakdown",
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.75)",
        coloraxis_showscale=False,
        font=dict(family="Instrument Sans"),
    )
    st.plotly_chart(figure, use_container_width=True)


def filter_sidebar(prefix: str = "filters") -> dict[str, Any]:
    with st.sidebar:
        st.subheader("Filters")
        keyword = st.text_input("Keyword", key=f"{prefix}_keyword")
        query = st.text_input("Full-text query", key=f"{prefix}_query", help="Uses SQLite FTS5 syntax.")
        source = st.selectbox("Source", ["", "reddit", "hacker_news", "discourse"], key=f"{prefix}_source")
        community = st.text_input("Community", key=f"{prefix}_community")
        tag = st.text_input("Tag", key=f"{prefix}_tag")
        tag_type = st.selectbox("Tag type", ["", "audience", "problem_type", "solution_type"], key=f"{prefix}_tag_type")
        solution_type = st.selectbox(
            "Likely solution",
            ["", "mobile_app", "simple_web_app", "micro_saas", "directory", "marketplace", "browser_extension", "ai_assistant", "workflow_automation", "service_business", "content_community_product", "template_product"],
            key=f"{prefix}_solution_type",
        )
        start_date = st.date_input("Start date", value=None, key=f"{prefix}_start")
        end_date = st.date_input("End date", value=None, key=f"{prefix}_end")
        min_score = st.slider("Minimum score", 0.0, 10.0, 0.0, 0.5, key=f"{prefix}_min_score")
        self_serve_only = st.checkbox("Self-serve friendly only", key=f"{prefix}_self_serve")
        saved_only = st.checkbox("Saved only", key=f"{prefix}_saved")
        dismissed_only = st.checkbox("Dismissed only", key=f"{prefix}_dismissed")
        sort_by = st.selectbox("Sort by", ["overall_score", "created_at", "source_score"], key=f"{prefix}_sort")
        limit = st.slider("Rows", 10, 200, 50, 10, key=f"{prefix}_limit")
    return {
        "keyword": keyword,
        "query": query,
        "source": source,
        "community": community,
        "tag": tag,
        "tag_type": tag_type,
        "solution_type": solution_type,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "min_score": min_score if min_score > 0 else None,
        "self_serve_only": self_serve_only,
        "saved_only": saved_only,
        "dismissed_only": dismissed_only,
        "sort_by": sort_by,
        "limit": limit,
    }
