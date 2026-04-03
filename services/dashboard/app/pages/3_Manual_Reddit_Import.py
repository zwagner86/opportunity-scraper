from __future__ import annotations

from urllib.parse import urlparse

import json
import streamlit as st

from app.api_client import APIClient
from app.ui import setup_page


setup_page("Manual Reddit Import")
client = APIClient()


def derive_community(url: str) -> str:
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if "r" in path_parts:
        try:
            return path_parts[path_parts.index("r") + 1]
        except IndexError:
            return "reddit"
    return "reddit"


def default_title(url: str) -> str:
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if "comments" in path_parts and len(path_parts) >= path_parts.index("comments") + 3:
        return path_parts[path_parts.index("comments") + 2].replace("_", " ").replace("-", " ").strip()
    return ""


def parse_comments_blob(blob: str) -> list[dict[str, object]]:
    comments = []
    for block in [section.strip() for section in blob.split("\n\n") if section.strip()]:
        comments.append({"body": block})
    return comments


st.title("Manual Reddit Import")
st.caption("Import handpicked Reddit threads where everyday people are clearly describing a recurring annoyance, workaround, or coordination mess.")
st.markdown(
    """
    <div class="hero-card">
        <div class="section-label">Workflow</div>
        <div style="font-size:1rem;line-height:1.6;color:#314240;">
            1. Paste thread URLs.
            2. Fill in the thread-level complaint you want analyzed.
            3. Optionally add only the top comments that strengthen the case.
            4. Preview and import.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Sample payload template", expanded=False):
    template = client.get("/imports/reddit-template")
    st.code(json.dumps(template, indent=2), language="json")

urls_text = st.text_area(
    "Reddit thread URLs",
    placeholder="https://www.reddit.com/r/parenting/comments/example/thread_slug/\nhttps://www.reddit.com/r/frugal/comments/example/another_thread/",
    height=120,
)

if st.button("Prepare import form", use_container_width=True):
    urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    st.session_state["reddit_manual_urls"] = urls
    st.success(f"Prepared {len(urls)} Reddit thread slot(s).")

urls = st.session_state.get("reddit_manual_urls", [])
if not urls:
    st.info("Paste one or more Reddit thread URLs and prepare the form to start a batch.")
    st.stop()

threads = []
for index, url in enumerate(urls):
    with st.expander(f"Thread {index + 1}: {url}", expanded=True):
        community = st.text_input("Community", value=derive_community(url), key=f"community_{index}")
        title = st.text_input("Title", value=default_title(url), key=f"title_{index}")
        body = st.text_area("Thread body", key=f"body_{index}", height=180)
        author = st.text_input("Author", key=f"author_{index}")
        score = st.number_input("Score", min_value=0.0, value=0.0, step=1.0, key=f"score_{index}")
        comments_count = st.number_input("Comment count", min_value=0, value=0, step=1, key=f"comments_count_{index}")
        comments_blob = st.text_area(
            "Top comments that reinforce the pain point (optional, separate comments with a blank line)",
            key=f"comments_blob_{index}",
            height=160,
        )
        threads.append(
            {
                "url": url,
                "community": community,
                "title": title,
                "body": body,
                "author": author or None,
                "score": score if score > 0 else None,
                "comments_count": comments_count if comments_count > 0 else None,
                "comments": parse_comments_blob(comments_blob),
            }
        )

valid_threads = [thread for thread in threads if thread["url"] and thread["community"] and thread["title"] and thread["body"]]

st.subheader("Batch preview")
if valid_threads:
    st.json({"threads": valid_threads}, expanded=False)
else:
    st.warning("Fill in at least the community, title, and body for one thread to preview/import.")

action_cols = st.columns(2)
with action_cols[0]:
    if st.button("Preview ready count", use_container_width=True):
        st.info(f"{len(valid_threads)} thread(s) are ready to import.")
with action_cols[1]:
    if st.button("Import batch", use_container_width=True, type="primary", disabled=not valid_threads):
        response = client.post("/imports/reddit-manual", {"threads": valid_threads})
        st.success(response["summary"])
        st.json(response)
