from __future__ import annotations

from types import SimpleNamespace


def test_reddit_adapter_normalizes_submission_and_comment(configured_env, monkeypatch):
    from app.adapters import reddit as reddit_module
    from app.adapters.reddit import RedditAdapter

    class FakeComment:
        def __init__(self):
            self.id = "c1"
            self.body = "I manually juggle this every week."
            self.author = "commenter"
            self.created_utc = 1_700_000_000
            self.score = 8
            self.parent_id = "t3_s1"
            self.depth = 0
            self.permalink = "/r/test/comments/s1/title/c1/"

    class FakeComments(list):
        def replace_more(self, limit=0):
            return None

    class FakeSubmission:
        def __init__(self):
            self.id = "s1"
            self.title = "Wish there was a better way to manage meal plans"
            self.selftext = "I built my own spreadsheet for this."
            self.author = "author"
            self.created_utc = 1_700_000_000
            self.score = 42
            self.num_comments = 12
            self.permalink = "/r/test/comments/s1/title/"
            self.link_flair_text = "Question"
            self.upvote_ratio = 0.95
            self.is_self = True
            self.comments = FakeComments([FakeComment()])

    class FakeSubreddit:
        def hot(self, limit=20):
            return [FakeSubmission()]

    class FakeReddit:
        def subreddit(self, name):
            return FakeSubreddit()

    monkeypatch.setattr(reddit_module.praw, "Reddit", lambda **_: FakeReddit())
    adapter = RedditAdapter()
    adapter.config["subreddits"] = ["test"]
    result = adapter.fetch(run_id=1, limit_override=1)

    assert len(result.items) == 2
    thread, comment = result.items
    assert thread.community == "test"
    assert thread.raw_metadata["link_flair_text"] == "Question"
    assert comment.content_type == "comment"
    assert comment.parent_source_item_id == "s1"


def test_hacker_news_adapter_normalizes_story_and_comment(configured_env, monkeypatch):
    from app.adapters.hacker_news import HackerNewsAdapter

    adapter = HackerNewsAdapter()
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
    assert story.content_type == "story"
    assert story.raw_metadata["feed"] == "ask"
    assert comment.parent_source_item_id == "101"


def test_discourse_adapter_normalizes_topic_and_post(configured_env, monkeypatch):
    from app.adapters.discourse import DiscourseAdapter

    adapter = DiscourseAdapter()
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
    assert topic.source_item_id == "forum:topic:9"
    assert post.parent_source_item_id == "forum:topic:9"
    assert topic.raw_metadata["forum"] == "forum"

