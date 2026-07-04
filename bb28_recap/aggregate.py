"""Merge, sort, and flag gaps across all fetched sources."""
from __future__ import annotations

from .models import RawPost, SourceResult


def aggregate_sources(results: list[SourceResult]) -> list[RawPost]:
    """Merge all posts across sources into one list, sorted oldest to newest."""
    all_posts: list[RawPost] = []
    for result in results:
        all_posts.extend(result.posts)
    return sorted(all_posts, key=lambda p: p.published_at)


def missing_sources(results: list[SourceResult]) -> list[str]:
    """Sources that returned zero posts - candidates for a 'possible scrape break' warning."""
    return [r.source for r in results if not r.found_any]


def render_raw_feed_text(posts: list[RawPost]) -> str:
    """Flatten into one text blob for the LLM prompt, each line tagged with source+time."""
    lines = [
        f"[{p.published_at.strftime('%H:%M')}] ({p.source}) {p.text}" for p in posts
    ]
    return "\n".join(lines)
