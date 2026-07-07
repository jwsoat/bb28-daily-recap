"""Local script: every 8 hours, run the full Claude extraction pass over RSS
and push any facts to HA - catches nominations/evictions/have-not/jury and
anything the 15-min keyword-sync script couldn't confidently parse or missed.
No email (that's the daily Vercel cron's job - see api/daily_recap.py).

Run via Windows Task Scheduler (see README for the schtasks command)."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from bb28_recap.aggregate import aggregate_sources, render_raw_feed_text
from bb28_recap.claude_response import extract_text_from_response
from bb28_recap.config import RSS_FEEDS
from bb28_recap.extract import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
    parse_extraction_response,
)
from bb28_recap.ha_push import build_ha_service_calls, push_service_calls
from bb28_recap.sources_rss import fetch_rss_source

load_dotenv(SCRIPT_DIR / ".env")


async def main() -> None:
    anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    ha_base_url = os.environ["HA_BASE_URL"]
    ha_token = os.environ["HA_LONG_LIVED_TOKEN"]

    now = datetime.now(timezone.utc)
    results = [fetch_rss_source(feed_url, now) for feed_url in RSS_FEEDS]
    posts = aggregate_sources(results)
    raw_feed_text = render_raw_feed_text(posts)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_extraction_prompt(raw_feed_text)}],
    )
    facts = parse_extraction_response(extract_text_from_response(response))

    if not facts:
        print("No facts extracted this run.")
        return

    calls = build_ha_service_calls(facts)
    async with httpx.AsyncClient() as session:
        push_results = await push_service_calls(session, ha_base_url, ha_token, calls)
    for result in push_results:
        status = "OK" if result.success else f"FAILED: {result.error}"
        print(f"{result.call.data} -> {status}")


if __name__ == "__main__":
    asyncio.run(main())
