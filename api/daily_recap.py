"""Vercel Cron entry point - the one place real clients get constructed.
No automated tests: verified by manual smoke test after deployment (see README).

X scraping is disabled for now (RSS-only) - see sources_x.py/tests_sources_x.py
for the tested-but-unwired twikit integration, kept for easy re-enabling later."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

import httpx
import resend
from anthropic import Anthropic

from bb28_recap.claude_response import extract_text_from_response
from bb28_recap.config import RECIPIENT_EMAIL, RSS_FEEDS, load_env_config
from bb28_recap.extract import EXTRACTION_SYSTEM_PROMPT
from bb28_recap.ha_push import build_ha_service_calls, push_service_calls
from bb28_recap.models import SourceResult
from bb28_recap.pipeline import run_daily_recap
from bb28_recap.sources_rss import fetch_rss_source
from bb28_recap.summarize import SUMMARY_SYSTEM_PROMPT


async def _fetch_all_rss(now: datetime) -> list[SourceResult]:
    results = []
    for feed_url in RSS_FEEDS:
        results.append(fetch_rss_source(feed_url, now))
    return results


async def _fetch_all_x(now: datetime) -> list[SourceResult]:
    """X scraping disabled for now - returns no sources. Re-enable by restoring
    the twikit-backed TwikitXClient wrapper and wiring it back into _run()."""
    return []


async def _run(env: dict) -> None:
    config = load_env_config(env)
    now = datetime.now(timezone.utc)

    anthropic_client = Anthropic(api_key=config["ANTHROPIC_API_KEY"])
    resend.api_key = config["RESEND_API_KEY"]

    async def fetch_rss_sources():
        return await _fetch_all_rss(now)

    async def fetch_x_sources():
        return await _fetch_all_x(now)

    async def call_claude_extract(prompt: str) -> str:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_text_from_response(response)

    async def call_claude_summarize(prompt: str) -> str:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_text_from_response(response)

    async def push_facts_to_ha(facts):
        calls = build_ha_service_calls(facts)
        async with httpx.AsyncClient() as session:
            return await push_service_calls(
                session, config["HA_BASE_URL"], config["HA_LONG_LIVED_TOKEN"], calls
            )

    async def send_email(content):
        resend.Emails.send(
            {
                "from": "BB28 Daily Recap <bigbrother@mechanicfinder.co.nz>",
                "to": [RECIPIENT_EMAIL],
                "subject": content.subject,
                "text": content.body,
            }
        )

    await run_daily_recap(
        now,
        fetch_rss_sources,
        fetch_x_sources,
        call_claude_extract,
        call_claude_summarize,
        push_facts_to_ha,
        send_email,
    )


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            asyncio.run(_run(dict(os.environ)))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as exc:  # noqa: BLE001 - surface the error in the response + logs
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(exc).encode())
            raise
