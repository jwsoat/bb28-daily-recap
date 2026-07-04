from datetime import datetime

from bb28_recap.aggregate import aggregate_sources, missing_sources, render_raw_feed_text
from bb28_recap.models import RawPost, SourceResult


def _post(source, text, hour):
    return RawPost(source=source, text=text, published_at=datetime(2026, 7, 10, hour, 0))


def test_aggregate_sources_merges_and_sorts_by_time():
    results = [
        SourceResult(source="x:a", posts=[_post("x:a", "second", 14)], found_any=True),
        SourceResult(source="rss:b", posts=[_post("rss:b", "first", 9)], found_any=True),
    ]
    posts = aggregate_sources(results)
    assert [p.text for p in posts] == ["first", "second"]


def test_aggregate_sources_handles_empty_results():
    assert aggregate_sources([]) == []


def test_missing_sources_returns_only_found_any_false():
    results = [
        SourceResult(source="x:a", posts=[_post("x:a", "hi", 9)], found_any=True),
        SourceResult(source="rss:b", posts=[], found_any=False),
    ]
    assert missing_sources(results) == ["rss:b"]


def test_missing_sources_empty_when_all_found():
    results = [SourceResult(source="x:a", posts=[_post("x:a", "hi", 9)], found_any=True)]
    assert missing_sources(results) == []


def test_render_raw_feed_text_formats_each_post():
    posts = [_post("x:a", "hello", 9)]
    text = render_raw_feed_text(posts)
    assert text == "[09:00] (x:a) hello"


def test_render_raw_feed_text_joins_multiple_lines():
    posts = [_post("x:a", "first", 9), _post("rss:b", "second", 14)]
    text = render_raw_feed_text(posts)
    assert text == "[09:00] (x:a) first\n[14:00] (rss:b) second"
