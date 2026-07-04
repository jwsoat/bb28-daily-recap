import time
from datetime import datetime, timedelta, timezone

from bb28_recap.sources_rss import fetch_rss_source, filter_recent_entries

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Sample BB Feed</title>
<item>
  <title>Recent Update</title>
  <description>Something happened today</description>
  <pubDate>{recent_date}</pubDate>
</item>
<item>
  <title>Old Update</title>
  <description>Something happened last week</description>
  <pubDate>{old_date}</pubDate>
</item>
</channel></rss>"""


def _rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def test_filter_recent_entries_excludes_entries_older_than_window():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    recent = time.struct_time((2026, 7, 10, 9, 0, 0, 0, 0, 0))
    old = time.struct_time((2026, 7, 1, 9, 0, 0, 0, 0, 0))
    entries = [
        {"title": "Recent", "summary": "", "published_parsed": recent},
        {"title": "Old", "summary": "", "published_parsed": old},
    ]
    posts = filter_recent_entries(entries, now)
    assert [p.text for p in posts] == ["Recent"]


def test_filter_recent_entries_skips_entries_with_no_published_date():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    entries = [{"title": "No date", "summary": "", "published_parsed": None}]
    assert filter_recent_entries(entries, now) == []


def test_filter_recent_entries_combines_title_and_summary():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    recent = time.struct_time((2026, 7, 10, 9, 0, 0, 0, 0, 0))
    entries = [{"title": "Title", "summary": "Body", "published_parsed": recent}]
    posts = filter_recent_entries(entries, now)
    assert posts[0].text == "Title: Body"


def test_fetch_rss_source_parses_real_feed_content_and_filters_and_tags():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    xml = SAMPLE_RSS.format(
        recent_date=_rfc822(datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)),
        old_date=_rfc822(datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)),
    )
    result = fetch_rss_source(xml, now)
    assert result.found_any is True
    assert len(result.posts) == 1
    assert result.posts[0].source.startswith("rss:")
    assert "Recent Update" in result.posts[0].text


def test_fetch_rss_source_found_any_false_when_nothing_recent():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    xml = SAMPLE_RSS.format(
        recent_date=_rfc822(datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)),
        old_date=_rfc822(datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)),
    )
    result = fetch_rss_source(xml, now)
    assert result.found_any is False
    assert result.posts == []
