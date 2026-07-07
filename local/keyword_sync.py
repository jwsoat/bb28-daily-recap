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


def load_housemate_aliases() -> dict[str, list[str]]:
    """Parse local/housemates.txt. Each non-comment line is either just a
    canonical name ("Alex") or "Alex: Alexander Smith, Al" - the canonical
    name is what the HA sensor is called; anything after the colon is extra
    name variants (nicknames, full legal names) to also search RSS text for."""
    if not HOUSEMATES_FILE.exists():
        return {}
    aliases: dict[str, list[str]] = {}
    for raw_line in HOUSEMATES_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            name, rest = line.split(":", 1)
            name = name.strip()
            extra = [alias.strip() for alias in rest.split(",") if alias.strip()]
        else:
            name = line
            extra = []
        if name:
            aliases[name] = extra
    return aliases


def load_seen_keys() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))


def save_seen_keys(keys: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(keys)), encoding="utf-8")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Missing required environment variable: {name} (check local/.env)")
        sys.exit(1)
    return value


async def main() -> None:
    ha_base_url = _require_env("HA_BASE_URL")
    ha_token = _require_env("HA_LONG_LIVED_TOKEN")

    housemate_aliases = load_housemate_aliases()
    if not housemate_aliases:
        print("No housemate names in local/housemates.txt yet - nothing to match, exiting.")
        return

    now = datetime.now(timezone.utc)
    results = [fetch_rss_source(feed_url, now) for feed_url in RSS_FEEDS]
    posts = aggregate_sources(results)

    seen_keys = load_seen_keys()
    new_posts = filter_unseen_posts(posts, seen_keys)

    facts = match_hoh_veto_facts(new_posts, housemate_aliases)

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
