"""Fetch and filter RSS feed entries."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import feedparser

from .models import RawPost, SourceResult


def filter_recent_entries(
    entries: list[dict], now: datetime, window: timedelta = timedelta(hours=24)
) -> list[RawPost]:
    cutoff = now - window
    posts = []
    for entry in entries:
        published_struct = entry.get("published_parsed")
        if published_struct is None:
            continue
        published_at = datetime(*published_struct[:6], tzinfo=timezone.utc)
        if published_at < cutoff:
            continue
        text = entry.get("title", "")
        summary = entry.get("summary", "")
        if summary:
            text = f"{text}: {summary}"
        posts.append(RawPost(source="", text=text, published_at=published_at))
    return posts


def fetch_rss_source(feed_url: str, now: datetime) -> SourceResult:
    parsed = feedparser.parse(feed_url)
    raw_posts = filter_recent_entries(parsed.entries, now)
    tagged_posts = [
        RawPost(source=f"rss:{feed_url}", text=p.text, published_at=p.published_at)
        for p in raw_posts
    ]
    return SourceResult(
        source=f"rss:{feed_url}", posts=tagged_posts, found_any=bool(tagged_posts)
    )
