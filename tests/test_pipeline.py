import asyncio
from datetime import datetime, timezone

from bb28_recap.models import RawPost, SourceResult
from bb28_recap.pipeline import run_daily_recap


def _make_deps(
    rss_results=None,
    x_results=None,
    extraction_response="[]",
    summary_response="outline text",
    push_results=None,
    raise_on_rss=False,
    raise_on_x=False,
):
    sent_emails = []

    async def fetch_rss_sources():
        if raise_on_rss:
            raise ConnectionError("rss down")
        return rss_results or []

    async def fetch_x_sources():
        if raise_on_x:
            raise ConnectionError("x down")
        return x_results or []

    async def call_claude_extract(prompt):
        return extraction_response

    async def call_claude_summarize(prompt):
        return summary_response

    async def push_facts_to_ha(facts):
        return push_results or []

    async def send_email(content):
        sent_emails.append(content)

    return (
        fetch_rss_sources,
        fetch_x_sources,
        call_claude_extract,
        call_claude_summarize,
        push_facts_to_ha,
        send_email,
        sent_emails,
    )


def test_happy_path_sends_email_with_correct_day_and_outline():
    now = datetime(2026, 7, 13, 3, 0, tzinfo=timezone.utc)
    post = RawPost(source="x:a", text="Alex won HOH", published_at=now)
    rss_results = []
    x_results = [SourceResult(source="x:a", posts=[post], found_any=True)]
    deps = _make_deps(rss_results=rss_results, x_results=x_results, summary_response="Today's outline")
    *fns, sent_emails = deps
    result = asyncio.run(run_daily_recap(now, *fns))
    assert result.subject == "BB28 Daily Recap — Day 4"
    assert "Today's outline" in result.body
    assert sent_emails == [result]


def test_rss_fetch_failure_does_not_abort_the_run():
    now = datetime(2026, 7, 12, 15, 0, tzinfo=timezone.utc)
    post = RawPost(source="x:a", text="Alex won HOH", published_at=now)
    x_results = [SourceResult(source="x:a", posts=[post], found_any=True)]
    deps = _make_deps(x_results=x_results, raise_on_rss=True)
    *fns, sent_emails = deps
    result = asyncio.run(run_daily_recap(now, *fns))
    assert len(sent_emails) == 1


def test_x_fetch_failure_does_not_abort_the_run():
    now = datetime(2026, 7, 12, 15, 0, tzinfo=timezone.utc)
    post = RawPost(source="rss:b", text="Jordan nominated", published_at=now)
    rss_results = [SourceResult(source="rss:b", posts=[post], found_any=True)]
    deps = _make_deps(rss_results=rss_results, raise_on_x=True)
    *fns, sent_emails = deps
    result = asyncio.run(run_daily_recap(now, *fns))
    assert len(sent_emails) == 1


def test_blank_extraction_response_does_not_abort_the_run():
    now = datetime(2026, 7, 12, 15, 0, tzinfo=timezone.utc)
    post = RawPost(source="rss:b", text="Jordan nominated", published_at=now)
    rss_results = [SourceResult(source="rss:b", posts=[post], found_any=True)]
    deps = _make_deps(rss_results=rss_results, extraction_response="")
    *fns, sent_emails = deps
    result = asyncio.run(run_daily_recap(now, *fns))
    assert len(sent_emails) == 1


def test_extraction_call_raising_does_not_abort_the_run():
    now = datetime(2026, 7, 12, 15, 0, tzinfo=timezone.utc)
    post = RawPost(source="rss:b", text="Jordan nominated", published_at=now)
    rss_results = [SourceResult(source="rss:b", posts=[post], found_any=True)]

    async def raising_extract(prompt):
        raise RuntimeError("Claude response had no text block")

    deps = _make_deps(rss_results=rss_results)
    fns = list(deps[:-1])
    sent_emails = deps[-1]
    fns[2] = raising_extract
    result = asyncio.run(run_daily_recap(now, *fns))
    assert len(sent_emails) == 1
