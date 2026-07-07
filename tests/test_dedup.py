from datetime import datetime, timezone

from bb28_recap.dedup import filter_unseen_posts, post_key
from bb28_recap.models import RawPost


def _post(text, source="rss:a"):
    return RawPost(
        source=source, text=text, published_at=datetime(2026, 7, 10, tzinfo=timezone.utc)
    )


def test_post_key_is_stable_for_same_source_and_text():
    assert post_key(_post("hello")) == post_key(_post("hello"))


def test_post_key_differs_for_different_text():
    assert post_key(_post("hello")) != post_key(_post("world"))


def test_post_key_differs_for_different_source():
    assert post_key(_post("hello", source="rss:a")) != post_key(_post("hello", source="rss:b"))


def test_filter_unseen_posts_excludes_seen_keys():
    seen = {post_key(_post("old news"))}
    posts = [_post("old news"), _post("new news")]
    result = filter_unseen_posts(posts, seen)
    assert [p.text for p in result] == ["new news"]


def test_filter_unseen_posts_empty_seen_returns_all():
    posts = [_post("a"), _post("b")]
    assert filter_unseen_posts(posts, set()) == posts


def test_filter_unseen_posts_empty_posts_returns_empty():
    assert filter_unseen_posts([], {"x"}) == []
