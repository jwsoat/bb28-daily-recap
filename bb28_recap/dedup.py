"""Track which posts have already been processed, so a still-recent post
sitting in the 24h RSS window doesn't get re-matched/re-pushed every run."""
from __future__ import annotations

from .models import RawPost


def post_key(post: RawPost) -> str:
    return f"{post.source}|{post.text}"


def filter_unseen_posts(posts: list[RawPost], seen_keys: set[str]) -> list[RawPost]:
    return [p for p in posts if post_key(p) not in seen_keys]
