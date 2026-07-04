"""Vercel Cron entry point - the one place real clients get constructed.
No automated tests: verified by manual smoke test after deployment (see README)."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

import httpx
import resend
from anthropic import Anthropic
from twikit import Client as TwikitClient

from bb28_recap.config import (
    RECIPIENT_EMAIL,
    RSS_FEEDS,
    X_ACCOUNTS,
    load_env_config,
)
from bb28_recap.extract import EXTRACTION_SYSTEM_PROMPT
from bb28_recap.ha_push import build_ha_service_calls, push_service_calls
from bb28_recap.models import SourceResult
from bb28_recap.pipeline import run_daily_recap
from bb28_recap.sources_rss import fetch_rss_source
from bb28_recap.sources_x import fetch_x_source
from bb28_recap.summarize import SUMMARY_SYSTEM_PROMPT


class TwikitXClient:
    """Wraps twikit.Client into the get_user_tweets(account) -> list[(text, datetime)]
    shape bb28_recap.sources_x.fetch_x_source expects. Verified against twikit==2.3.3
    (installed from requirements.txt): Client.login() takes auth_info_1/auth_info_2/
    password kwargs, get_user_by_screen_name(screen_name) -> User with .id,
    get_user_tweets(user_id, 'Tweets') -> iterable of Tweet with .text/.created_at_datetime."""

    def __init__(self, username: str, email: str, password: str) -> None:
        self._client = TwikitClient("en-US")
        self._username = username
        self._email = email
        self._password = password
        self._logged_in = False

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self._client.login(
                auth_info_1=self._username,
                auth_info_2=self._email,
                password=self._password,
            )
            self._logged_in = True

    async def get_user_tweets(self, account: str) -> list[tuple[str, datetime]]:
        await self._ensure_login()
        user = await self._client.get_user_by_screen_name(account)
        tweets = await self._client.get_user_tweets(user.id, "Tweets")
        return [(t.text, t.created_at_datetime) for t in tweets]


async def _fetch_all_rss(now: datetime) -> list[SourceResult]:
    results = []
    for feed_url in RSS_FEEDS:
        results.append(fetch_rss_source(feed_url, now))
    return results


async def _fetch_all_x(client: TwikitXClient, now: datetime) -> list[SourceResult]:
    results = []
    for account in X_ACCOUNTS:
        results.append(await fetch_x_source(client, account, now))
    return results


async def _run(env: dict) -> None:
    config = load_env_config(env)
    now = datetime.now(timezone.utc)

    x_client = TwikitXClient(
        config["X_BURNER_USERNAME"], config["X_BURNER_EMAIL"], config["X_BURNER_PASSWORD"]
    )
    anthropic_client = Anthropic(api_key=config["ANTHROPIC_API_KEY"])
    resend.api_key = config["RESEND_API_KEY"]

    async def fetch_rss_sources():
        return await _fetch_all_rss(now)

    async def fetch_x_sources():
        return await _fetch_all_x(x_client, now)

    async def call_claude_extract(prompt: str) -> str:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def call_claude_summarize(prompt: str) -> str:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    async def push_facts_to_ha(facts):
        calls = build_ha_service_calls(facts)
        async with httpx.AsyncClient() as session:
            return await push_service_calls(
                session, config["HA_BASE_URL"], config["HA_LONG_LIVED_TOKEN"], calls
            )

    async def send_email(content):
        resend.Emails.send(
            {
                "from": "BB28 Daily Recap <onboarding@resend.dev>",
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
