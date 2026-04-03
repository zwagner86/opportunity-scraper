from __future__ import annotations

import logging

import praw

from app.adapters.base import SourceAdapter
from app.config.loader import load_app_config
from app.config.settings import get_settings
from app.models.domain import FetchResult, IngestionError
from app.services.normalizer import Normalizer, epoch_to_datetime


logger = logging.getLogger(__name__)


class RedditAdapter(SourceAdapter):
    source_name = "reddit"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.config = load_app_config().sources.reddit
        self.normalizer = Normalizer()

    def fetch(self, *, run_id: int, limit_override: int | None = None) -> FetchResult:
        result = FetchResult()
        if not self.config.get("enabled", False):
            return result
        if not (
            self.settings.reddit_client_id
            and self.settings.reddit_client_secret
            and self.settings.reddit_user_agent
        ):
            result.errors.append(
                IngestionError(
                    source=self.source_name,
                    message="Missing Reddit API credentials; skipping Reddit source.",
                )
            )
            return result

        reddit = praw.Reddit(
            client_id=self.settings.reddit_client_id,
            client_secret=self.settings.reddit_client_secret,
            user_agent=self.settings.reddit_user_agent,
        )
        listing_mode = self.config.get("listing_mode", "hot")
        per_subreddit_limit = self.limit_value(self.config.get("per_subreddit_limit"), limit_override) or 20
        comment_limit = self.limit_value(self.config.get("top_level_comment_limit"), limit_override) or 10

        for subreddit_name in self.config.get("subreddits", []):
            try:
                subreddit = reddit.subreddit(subreddit_name)
                listing = getattr(subreddit, listing_mode)(limit=per_subreddit_limit)
                for submission in listing:
                    result.items.append(
                        self.normalizer.normalize(
                            source=self.source_name,
                            community=subreddit_name,
                            source_item_id=submission.id,
                            url=f"https://www.reddit.com{submission.permalink}",
                            title=submission.title,
                            body=submission.selftext or "",
                            author=str(submission.author) if submission.author else None,
                            created_at=epoch_to_datetime(submission.created_utc),
                            score=float(submission.score or 0),
                            comments_count=int(submission.num_comments or 0),
                            raw_metadata={
                                "permalink": submission.permalink,
                                "link_flair_text": submission.link_flair_text,
                                "upvote_ratio": getattr(submission, "upvote_ratio", None),
                                "is_self": submission.is_self,
                            },
                            content_type="thread",
                            parent_source_item_id=None,
                            ingestion_run_id=run_id,
                        )
                    )
                    submission.comment_sort = "top"
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments[:comment_limit]:
                        body = getattr(comment, "body", "") or ""
                        if not body or body in {"[deleted]", "[removed]"}:
                            continue
                        result.items.append(
                            self.normalizer.normalize(
                                source=self.source_name,
                                community=subreddit_name,
                                source_item_id=comment.id,
                                url=f"https://www.reddit.com{comment.permalink}",
                                title=f"Comment on: {submission.title}",
                                body=body,
                                author=str(comment.author) if comment.author else None,
                                created_at=epoch_to_datetime(comment.created_utc),
                                score=float(comment.score or 0),
                                comments_count=None,
                                raw_metadata={
                                    "submission_id": submission.id,
                                    "submission_title": submission.title,
                                    "parent_id": comment.parent_id,
                                    "depth": getattr(comment, "depth", 0),
                                    "permalink": comment.permalink,
                                },
                                content_type="comment",
                                parent_source_item_id=submission.id,
                                ingestion_run_id=run_id,
                            )
                        )
            except Exception as exc:
                logger.exception("Reddit fetch failed")
                result.errors.append(
                    IngestionError(
                        source=self.source_name,
                        community=subreddit_name,
                        message=str(exc),
                        metadata={"listing_mode": listing_mode},
                    )
                )
        return result

