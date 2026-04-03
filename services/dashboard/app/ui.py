from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


INGESTION_METHOD_LABELS = {
    "manual_reddit_url": "Manual Reddit Import",
    "api_hacker_news": "Hacker News API",
    "json_discourse": "Discourse JSON",
    "rss_discourse": "Discourse RSS",
    "api_stackexchange": "Stack Exchange API",
    "rss_generic": "Generic RSS",
    "html_generic": "Generic HTML",
    "mixed": "Mixed Sources",
    "legacy": "Legacy Import",
}

SOURCE_LABELS = {
    "reddit": "Reddit",
    "hacker_news": "Hacker News",
    "discourse": "Discourse",
    "stack_exchange": "Stack Exchange",
    "rss_generic": "Public RSS Feed",
    "html_generic": "Public HTML Source",
}

CONTENT_ROLE_LABELS = {
    "primary_candidate": "Candidate",
    "supporting_comment": "Evidence Only",
    "background": "Suppressed",
}


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
            --bg: #f7f4ee;
            --card: #fffdf9;
            --ink: #223030;
            --accent: #1a6d60;
            --accent-soft: #dcefe9;
            --muted: #64736f;
            --line: rgba(34, 48, 48, 0.12);
            --shadow: 0 14px 40px rgba(35, 44, 44, 0.08);
            --sidebar: #23252f;
            --sidebar-ink: #f5f2ea;
            --sidebar-muted: #b8bdc8;
            --warning: #fff5df;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(202, 165, 93, 0.16), transparent 26%),
                radial-gradient(circle at top right, rgba(26, 109, 96, 0.18), transparent 24%),
                linear-gradient(180deg, #fbf8f2 0%, #f3eee3 100%);
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
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: var(--shadow);
        }
        .hero-card {
            background: linear-gradient(135deg, rgba(255,253,249,0.98) 0%, rgba(237,246,242,0.95) 100%);
            border: 1px solid rgba(26, 109, 96, 0.14);
            border-radius: 24px;
            padding: 1.35rem 1.4rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }
        .section-label {
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .empty-card {
            background: rgba(248, 242, 230, 0.72);
            border: 1px dashed rgba(34, 48, 48, 0.16);
            color: var(--ink);
            border-radius: 16px;
            padding: 1rem 1.05rem;
            min-height: 132px;
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
        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }
        [data-testid="stSidebar"] * {
            color: var(--sidebar-ink);
        }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] .stTextInput p {
            color: var(--sidebar-ink) !important;
        }
        [data-testid="stSidebar"] .stCaption {
            color: var(--sidebar-muted) !important;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 14px;
            font-weight: 700;
            border: 1px solid rgba(26, 109, 96, 0.18);
            background: #f7fbf9;
            color: var(--ink);
            min-height: 2.85rem;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #1a6d60 0%, #21564f 100%);
            color: #fbf9f5;
            border: none;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: rgba(26, 109, 96, 0.35);
            color: var(--ink);
        }
        div.stPageLink a {
            display: block;
            text-decoration: none;
            text-align: center;
            padding: 0.82rem 0.9rem;
            border-radius: 14px;
            background: rgba(255, 253, 249, 0.92);
            border: 1px solid rgba(26, 109, 96, 0.18);
            color: var(--ink) !important;
            font-weight: 700;
            box-shadow: 0 6px 16px rgba(35, 44, 44, 0.05);
        }
        div.stPageLink a:hover {
            background: #f1f8f5;
            border-color: rgba(26, 109, 96, 0.35);
        }
        [data-testid="stInfo"], [data-testid="stSuccess"], [data-testid="stWarning"] {
            border-radius: 14px;
            color: var(--ink);
        }
        [data-testid="stInfo"] {
            background: #eef6f6;
        }
        [data-testid="stWarning"] {
            background: var(--warning);
        }
        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            overflow: hidden;
            background: rgba(255, 253, 249, 0.9);
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


def format_ingestion_method(value: str | None) -> str:
    if not value:
        return "Unknown"
    return INGESTION_METHOD_LABELS.get(value, value.replace("_", " ").title())


def format_source_name(value: str | None) -> str:
    if not value:
        return "Unknown"
    return SOURCE_LABELS.get(value, value.replace("_", " ").title())


def format_content_role(value: str | None) -> str:
    if not value:
        return "Unknown"
    return CONTENT_ROLE_LABELS.get(value, value.replace("_", " ").title())


def render_empty_state_card(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="empty-card">
            <div style="font-weight:700;margin-bottom:0.35rem;">{title}</div>
            <div class="muted">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_distribution_chart(title: str, data: list[dict[str, Any]], x: str, y: str):
    df = pd.DataFrame(data)
    if df.empty:
        render_empty_state_card(title, f"No data available for {title.lower()} yet. Run an ingestion pass or import a few Reddit threads to populate this section.")
        return
    figure = px.bar(df, x=x, y=y, title=title, color=y, color_continuous_scale="Tealgrn")
    figure.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.82)",
        coloraxis_showscale=False,
        font=dict(family="Instrument Sans", color="#223030"),
        xaxis_title=None,
        yaxis_title=None,
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
        st.markdown("### Everyday-Life Candidates")
        st.caption("The app opens in candidate-only mode so you see complaint-first opportunities before supporting chatter.")
        keyword = st.text_input("Keyword", key=f"{prefix}_keyword")
        query = st.text_input("Full-text query", key=f"{prefix}_query", help="Uses SQLite FTS5 syntax.")
        candidate_only = st.checkbox("Candidate opportunities only", value=True, key=f"{prefix}_candidate_only")
        include_supporting = st.checkbox(
            "Include supporting comments",
            value=False,
            key=f"{prefix}_include_supporting",
            help="Bring in evidence-only comments alongside primary candidates.",
        )
        content_role = st.selectbox(
            "Content role",
            ["", "primary_candidate", "supporting_comment", "background"],
            format_func=lambda value: "Any role" if value == "" else format_content_role(value),
            key=f"{prefix}_content_role",
        )
        source = st.selectbox(
            "Source",
            ["", "reddit", "hacker_news", "discourse", "stack_exchange", "rss_generic", "html_generic"],
            format_func=lambda value: "All sources" if value == "" else format_source_name(value),
            key=f"{prefix}_source",
        )
        ingestion_method = st.selectbox(
            "Ingestion method",
            ["", "manual_reddit_url", "api_hacker_news", "json_discourse", "rss_discourse", "api_stackexchange", "rss_generic", "html_generic"],
            format_func=lambda value: "All methods" if value == "" else format_ingestion_method(value),
            key=f"{prefix}_ingestion_method",
        )
        community = st.text_input("Community", key=f"{prefix}_community")
        tag = st.text_input("Tag", key=f"{prefix}_tag")
        tag_type = st.selectbox(
            "Tag type",
            ["", "audience", "problem_type", "solution_type"],
            format_func=lambda value: "Any tag type" if value == "" else value.replace("_", " ").title(),
            key=f"{prefix}_tag_type",
        )
        solution_type = st.selectbox(
            "Likely solution",
            ["", "mobile_app", "simple_web_app", "micro_saas", "directory", "marketplace", "browser_extension", "ai_assistant", "workflow_automation", "service_business", "content_community_product", "template_product"],
            format_func=lambda value: "Any solution type" if value == "" else value.replace("_", " ").title(),
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
        "candidate_only": candidate_only,
        "include_supporting": include_supporting,
        "content_role": content_role,
        "source": source,
        "ingestion_method": ingestion_method,
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
