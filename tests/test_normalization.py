from __future__ import annotations


def test_hacker_news_adapter_normalizes_story_and_comment(configured_env, monkeypatch):
    from app.adapters.hacker_news import HackerNewsAdapter

    adapter = HackerNewsAdapter()
    adapter.config["enabled"] = True
    adapter.config["feeds"] = ["ask"]

    def fake_get_json(url: str):
        if url.endswith("/askstories.json"):
            return [101]
        if url.endswith("/item/101.json"):
            return {
                "id": 101,
                "title": "Is there a tool for tracking household chores?",
                "text": "<p>I keep a spreadsheet for this.</p>",
                "by": "hnuser",
                "time": 1_700_000_000,
                "score": 33,
                "descendants": 4,
                "kids": [202],
            }
        return {
            "id": 202,
            "text": "<p>I would use that every day.</p>",
            "by": "commenter",
            "time": 1_700_000_010,
            "kids": [],
            "parent": 101,
        }

    monkeypatch.setattr(adapter, "_get_json", fake_get_json)
    result = adapter.fetch(run_id=3, limit_override=1)

    assert len(result.items) == 2
    story, comment = result.items
    assert story.ingestion_method == "api_hacker_news"
    assert story.content_type == "story"
    assert story.raw_metadata["feed"] == "ask"
    assert comment.parent_source_item_id == "101"


def test_discourse_adapter_normalizes_topic_and_post(configured_env, monkeypatch):
    from app.adapters.discourse import DiscourseAdapter

    adapter = DiscourseAdapter()
    adapter.config["enabled"] = True
    adapter.config["forums"] = [{"name": "forum", "base_url": "https://forum.example.com", "mode": "json", "latest_limit": 1, "comment_limit": 1}]

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def fake_get(url: str, timeout: int = 20):
        if url.endswith("/latest.json"):
            return FakeResponse(
                {
                    "topic_list": {
                        "topics": [
                            {
                                "id": 9,
                                "slug": "better-pet-tracking",
                                "title": "Better pet tracking",
                                "posts_count": 2,
                                "like_count": 3,
                                "tags": ["pets"],
                            }
                        ]
                    }
                }
            )
        return FakeResponse(
            {
                "title": "Better pet tracking",
                "post_stream": {
                    "posts": [
                        {"id": 1, "username": "alice", "created_at": "2025-01-01T00:00:00Z", "cooked": "<p>Wish there was an easier app.</p>"},
                        {"id": 2, "username": "bob", "created_at": "2025-01-01T01:00:00Z", "cooked": "<p>I use a checklist.</p>", "post_number": 2, "reply_count": 0, "reply_to_post_number": 1},
                    ]
                },
            }
        )

    monkeypatch.setattr(adapter.session, "get", fake_get)
    result = adapter.fetch(run_id=5, limit_override=1)

    assert len(result.items) == 2
    topic, post = result.items
    assert topic.ingestion_method == "json_discourse"
    assert topic.source_item_id == "forum:topic:9"
    assert post.parent_source_item_id == "forum:topic:9"
    assert topic.raw_metadata["forum"] == "forum"


def test_stack_exchange_adapter_normalizes_question_and_answer(configured_env, monkeypatch):
    from app.adapters.stack_exchange import StackExchangeAdapter

    adapter = StackExchangeAdapter()
    adapter.config["enabled"] = True
    adapter.config["queries"] = [{"site": "webapps", "community": "webapps_productivity", "tags": "productivity"}]

    def fake_get_json(path: str, params: dict[str, object]):
        if path == "/questions":
            return {
                "items": [
                    {
                        "question_id": 11,
                        "title": "How do I track chores without a spreadsheet?",
                        "body": "<p>Need a better workflow.</p>",
                        "link": "https://webapps.stackexchange.com/questions/11",
                        "creation_date": 1_700_000_000,
                        "score": 18,
                        "answer_count": 1,
                        "tags": ["productivity"],
                        "is_answered": True,
                        "view_count": 200,
                        "owner": {"display_name": "asker"},
                    }
                ]
            }
        return {
            "items": [
                {
                    "answer_id": 12,
                    "body": "<p>I use a checklist app.</p>",
                    "link": "https://webapps.stackexchange.com/a/12",
                    "creation_date": 1_700_000_100,
                    "score": 7,
                    "comment_count": 0,
                    "is_accepted": True,
                    "owner": {"display_name": "answerer"},
                }
            ]
        }

    monkeypatch.setattr(adapter, "_get_json", fake_get_json)
    result = adapter.fetch(run_id=7, limit_override=1)

    assert len(result.items) == 2
    question, answer = result.items
    assert question.ingestion_method == "api_stackexchange"
    assert question.source_item_id == "webapps:q:11"
    assert answer.parent_source_item_id == "webapps:q:11"


def test_generic_rss_adapter_normalizes_entry(configured_env, monkeypatch):
    from types import SimpleNamespace

    from app.adapters.rss_generic import GenericRssAdapter
    import app.adapters.rss_generic as rss_module

    adapter = GenericRssAdapter()
    adapter.config["enabled"] = True
    adapter.config["feeds"] = [{"name": "obsidian_forum", "feed_url": "https://forum.obsidian.md/latest.rss", "limit": 1}]

    monkeypatch.setattr(
        rss_module.feedparser,
        "parse",
        lambda _: SimpleNamespace(entries=[{"id": "abc", "link": "https://forum.obsidian.md/t/abc", "title": "Need a better note workflow", "summary": "<p>I still use a spreadsheet.</p>", "author": "user", "published": "2026-01-01T00:00:00Z"}]),
    )
    result = adapter.fetch(run_id=9, limit_override=1)

    assert len(result.items) == 1
    entry = result.items[0]
    assert entry.source == "rss_generic"
    assert entry.ingestion_method == "rss_generic"
    assert entry.community == "obsidian_forum"


def test_html_generic_adapter_normalizes_public_html_source(configured_env, monkeypatch):
    from app.adapters.html_generic import HtmlGenericAdapter

    adapter = HtmlGenericAdapter()
    adapter.config["enabled"] = True
    adapter.config["sources"] = [
        {
            "name": "public_forum",
            "community": "parents",
            "list_url": "https://forum.example.com/latest",
            "item_selector": ["li.thread"],
            "title_selector": ["a.title"],
            "link_selector": ["a.title"],
            "summary_selector": ["p.summary"],
            "author_selector": ["span.author"],
            "content_type": "thread",
            "limit": 2,
        }
    ]

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    html = """
    <html>
      <body>
        <ul class="threads">
          <li class="thread">
            <a class="title" href="/threads/1">Need a better school pickup routine</a>
            <p class="summary">I keep a spreadsheet and text everyone every afternoon.</p>
            <span class="author">alex</span>
          </li>
        </ul>
      </body>
    </html>
    """

    monkeypatch.setattr(adapter.session, "get", lambda url, headers=None, timeout=20: FakeResponse(html))
    result = adapter.fetch(run_id=11, limit_override=1)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.source == "html_generic"
    assert item.ingestion_method == "html_generic"
    assert item.community == "parents"
    assert item.url == "https://forum.example.com/threads/1"
    assert item.title == "Need a better school pickup routine"
