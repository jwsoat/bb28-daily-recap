"""Local script: every 15 min, keyword-match RSS titles for HOH/Veto wins and
push directly to HA - no Claude call, free to run as often as you like.

Run via Windows Task Scheduler (see README for the schtasks command). Reads
secrets from local/.env and the housemate roster from local/housemates.txt -
copy local/housemates.example.txt to get started."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from bb28_recap.aggregate import aggregate_sources
from bb28_recap.config import RSS_FEEDS
from bb28_recap.dedup import filter_unseen_posts, post_key
from bb28_recap.ha_push import build_ha_service_calls, push_service_calls
from bb28_recap.keyword_match import match_hoh_veto_facts
from bb28_recap.sources_rss import fetch_rss_source

load_dotenv(SCRIPT_DIR / ".env")

HOUSEMATES_FILE = SCRIPT_DIR / "housemates.txt"
SEEN_FILE = SCRIPT_DIR / "keyword_seen.json"


def load_housemate_names() -> list[str]:
    if not HOUSEMATES_FILE.exists():
        return []
    lines = HOUSEMATES_FILE.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def load_seen_keys() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))


def save_seen_keys(keys: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(keys)), encoding="utf-8")


async def main() -> None:
    ha_base_url = os.environ["HA_BASE_URL"]
    ha_token = os.environ["HA_LONG_LIVED_TOKEN"]

    housemate_names = load_housemate_names()
    if not housemate_names:
        print("No housemate names in local/housemates.txt yet - nothing to match, exiting.")
        return

    now = datetime.now(timezone.utc)
    results = [fetch_rss_source(feed_url, now) for feed_url in RSS_FEEDS]
    posts = aggregate_sources(results)

    seen_keys = load_seen_keys()
    new_posts = filter_unseen_posts(posts, seen_keys)

    facts = match_hoh_veto_facts(new_posts, housemate_names)

    if facts:
        calls = build_ha_service_calls(facts)
        async with httpx.AsyncClient() as session:
            push_results = await push_service_calls(session, ha_base_url, ha_token, calls)
        for result in push_results:
            status = "OK" if result.success else f"FAILED: {result.error}"
            print(f"{result.call.data} -> {status}")
    else:
        print("No HOH/Veto keyword matches this run.")

    seen_keys.update(post_key(p) for p in posts)
    save_seen_keys(seen_keys)


if __name__ == "__main__":
    asyncio.run(main())
