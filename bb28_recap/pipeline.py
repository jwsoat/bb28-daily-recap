"""Orchestrate the full daily recap pipeline. Zero direct network/SDK calls -
every I/O operation is an injected async callable, making this fully testable
with fakes."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .aggregate import aggregate_sources, missing_sources, render_raw_feed_text
from .config import BB28_TIMEZONE, compute_day_number
from .email_content import build_email_content
from .extract import build_extraction_prompt, parse_extraction_response
from .models import EmailContent, SourceResult
from .summarize import build_summary_prompt, render_facts_text


async def run_daily_recap(
    now: datetime,
    fetch_rss_sources,  # async () -> list[SourceResult]
    fetch_x_sources,  # async () -> list[SourceResult]
    call_claude_extract,  # async (prompt: str) -> str (raw response text)
    call_claude_summarize,  # async (prompt: str) -> str
    push_facts_to_ha,  # async (facts: list[Fact]) -> list[PushResult]
    send_email,  # async (EmailContent) -> None
) -> EmailContent:
    try:
        rss_results = await fetch_rss_sources()
    except Exception:  # noqa: BLE001 - a fetch outage degrades to "found nothing", not a crash
        rss_results = []

    try:
        x_results = await fetch_x_sources()
    except Exception:  # noqa: BLE001
        x_results = []

    all_results: list[SourceResult] = rss_results + x_results
    posts = aggregate_sources(all_results)
    raw_feed_text = render_raw_feed_text(posts)
    missing = missing_sources(all_results)

    try:
        extraction_response = await call_claude_extract(build_extraction_prompt(raw_feed_text))
        facts = parse_extraction_response(extraction_response)
    except Exception:  # noqa: BLE001 - an extraction glitch (empty/malformed Claude
        # response) degrades to "no facts found this run", not a crash that blocks
        # the whole day's email - matches the RSS/X fetch failure handling above.
        facts = []

    push_results = await push_facts_to_ha(facts)

    facts_text = render_facts_text(facts)
    outline = await call_claude_summarize(build_summary_prompt(raw_feed_text, facts_text))

    day_number = compute_day_number(now.astimezone(ZoneInfo(BB28_TIMEZONE)).date())
    email_content = build_email_content(day_number, outline, push_results, missing)

    await send_email(email_content)
    return email_content
