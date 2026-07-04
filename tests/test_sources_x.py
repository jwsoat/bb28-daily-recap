import asyncio
from datetime import datetime, timezone

from bb28_recap.sources_x import fetch_x_source, filter_recent_posts


class FakeClient:
    def __init__(self, tweets):
        self._tweets = tweets

    async def get_user_tweets(self, account):
        return self._tweets


def test_filter_recent_posts_excludes_old_posts():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    posts = [
        ("recent", datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)),
        ("old", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)),
    ]
    result = filter_recent_posts(posts, now)
    assert [text for text, _ in result] == ["recent"]


def test_filter_recent_posts_empty_input():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    assert filter_recent_posts([], now) == []


def test_fetch_x_source_tags_and_filters_via_injected_client():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    client = FakeClient(
        [
            ("recent tweet", datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)),
            ("old tweet", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)),
        ]
    )
    result = asyncio.run(fetch_x_source(client, "SomeAccount", now))
    assert result.found_any is True
    assert len(result.posts) == 1
    assert result.posts[0].source == "x:SomeAccount"
    assert result.posts[0].text == "recent tweet"


def test_fetch_x_source_found_any_false_when_nothing_recent():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    client = FakeClient([("old tweet", datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc))])
    result = asyncio.run(fetch_x_source(client, "SomeAccount", now))
    assert result.found_any is False
    assert result.posts == []
