"""Fetch and filter X (Twitter) posts via an injected client."""
from __future__ import annotations

from datetime import datetime, timedelta

from .models import RawPost, SourceResult


def filter_recent_posts(
    raw_posts: list[tuple[str, datetime]],
    now: datetime,
    window: timedelta = timedelta(hours=24),
) -> list[tuple[str, datetime]]:
    cutoff = now - window
    return [(text, ts) for text, ts in raw_posts if ts >= cutoff]


async def fetch_x_source(client, account: str, now: datetime) -> SourceResult:
    """client must expose an async get_user_tweets(account) -> list[(text, datetime)]."""
    raw = await client.get_user_tweets(account)
    recent = filter_recent_posts(raw, now)
    posts = [
        RawPost(source=f"x:{account}", text=text, published_at=ts) for text, ts in recent
    ]
    return SourceResult(source=f"x:{account}", posts=posts, found_any=bool(posts))
