# Local BB28 HA Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two local scripts (run via Windows Task Scheduler, not Vercel) that push HA sensor updates far more often than the once-daily email cron: a free 15-minute keyword-matching pass for HOH/Veto wins, and an 8-hour Claude-extraction pass that catches nominations/evictions/have-not/jury facts and anything the keyword pass missed.

**Architecture:** Both scripts reuse the already-tested `bb28_recap/*` modules (RSS fetch, aggregate, HA push, Claude extraction) with zero duplication — the only new logic is a pure keyword-matching module, a pure dedup module, and a shared Claude-response-parsing helper (also back-ported into the existing Vercel entry point to remove a duplicate). The two local scripts themselves are thin glue (no automated tests, matching this project's existing convention for entry-point files that construct real clients), driven by a local `.env` file and a plain-text housemate roster the user maintains by hand.

**Tech Stack:** Python (same stack as the rest of `bb28-daily-recap`), `python-dotenv` (new — local secret loading), Windows Task Scheduler (`schtasks` CLI).

## Global Constraints

- Keyword matching ONLY ever produces `HOH` or `Veto Winner` facts — never nominations, evictions, have-not, or jury. Those always require the Claude extraction pass; do not extend keyword matching to cover them in this plan.
- Housemate status strings pushed to HA must exactly match the existing `big_brother_28` integration's valid values: `"HOH"` and `"Veto Winner"` (verbatim, case-sensitive).
- The 15-minute script must not call any paid API (no Anthropic client, no import of `anthropic` anywhere in `local/keyword_sync.py`).
- The 8-hour script does not send email and does not call the RSS-only source module for X (X scraping stays disabled per the existing `bb28_recap/sources_x.py` note — do not re-enable it in this plan).
- Local secrets load from a `.env` file via `python-dotenv`; the actual `.env` and the actual housemate roster (`local/housemates.txt`) are user-maintained, gitignored, and must never be committed — only `.example` templates are committed.
- Existing tests (52 as of the last shipped release) must all still pass after every task; this plan's new pure modules get the same full TDD treatment as the rest of the codebase.

---

### Task 1: Shared Claude-response text extraction + de-duplicate existing usage

**Files:**
- Create: `bb28_recap/claude_response.py`
- Create: `tests/test_claude_response.py`
- Modify: `api/daily-recap.py` → already renamed to `api/daily_recap.py` in a prior fix; modify that file to import and use the shared helper instead of its private duplicate.

**Interfaces:**
- Produces: `claude_response.extract_text_from_response(response) -> str` — consumed by Task 5 (the new 8-hour local script) and by the existing `api/daily_recap.py` (refactored in this task, not duplicated again).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_claude_response.py`:

```python
import pytest

from bb28_recap.claude_response import extract_text_from_response


class FakeBlock:
    def __init__(self, type_, text=None):
        self.type = type_
        if text is not None:
            self.text = text


class FakeResponse:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


def test_extract_text_from_response_finds_text_block():
    response = FakeResponse([FakeBlock("text", "hello")])
    assert extract_text_from_response(response) == "hello"


def test_extract_text_from_response_skips_non_text_blocks_first():
    response = FakeResponse([FakeBlock("thinking"), FakeBlock("text", "the answer")])
    assert extract_text_from_response(response) == "the answer"


def test_extract_text_from_response_raises_with_diagnostics_when_no_text_block():
    response = FakeResponse([FakeBlock("thinking")], stop_reason="max_tokens")
    with pytest.raises(RuntimeError, match="max_tokens"):
        extract_text_from_response(response)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_claude_response.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bb28_recap.claude_response'`

- [ ] **Step 3: Write the implementation**

Create `bb28_recap/claude_response.py`:

```python
"""Extract the text block from a Claude API response, tolerant of block
ordering (thinking blocks, refusals, etc. appearing before the actual text) -
assuming content[0] is always the text block previously caused a production
bug where an empty/non-text block silently produced an empty string."""
from __future__ import annotations


def extract_text_from_response(response) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    block_types = [getattr(b, "type", type(b).__name__) for b in response.content]
    raise RuntimeError(
        f"Claude response had no text block (stop_reason={response.stop_reason!r}, "
        f"block_types={block_types!r})"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_claude_response.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Refactor `api/daily_recap.py` to use the shared helper**

Read the current `api/daily_recap.py` first. It currently has a private `_extract_text_from_response` function defined near the top and two call sites (`call_claude_extract`, `call_claude_summarize`) that call it. Replace the private function definition with an import, and leave the two call sites unchanged (same function name, same behavior):

Remove this block entirely from `api/daily_recap.py`:

```python
def _extract_text_from_response(response) -> str:
    """Find the first text block in a Claude response, rather than assuming
    content[0] always is one - a differently-ordered or non-text block there
    (e.g. thinking/refusal) would otherwise silently produce an empty string."""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    block_types = [getattr(b, "type", type(b).__name__) for b in response.content]
    raise RuntimeError(
        f"Claude response had no text block (stop_reason={response.stop_reason!r}, "
        f"block_types={block_types!r})"
    )
```

Add this import near the top of `api/daily_recap.py`, alphabetically with the other `bb28_recap` imports:

```python
from bb28_recap.claude_response import extract_text_from_response
```

Then update the two call sites — everywhere the file currently calls `_extract_text_from_response(response)`, call `extract_text_from_response(response)` instead (same argument, just the imported name instead of the removed local function).

- [ ] **Step 6: Compile-check and run the full suite**

Run: `python -m py_compile api/daily_recap.py bb28_recap/*.py`
Expected: no output, exit code 0

Run: `python -m pytest tests/ -v`
Expected: all tests pass (52 existing + 3 new = 55)

- [ ] **Step 7: Commit**

```bash
git add bb28_recap/claude_response.py tests/test_claude_response.py api/daily_recap.py
git commit -m "refactor: extract shared Claude response text helper, dedupe from api/daily_recap.py"
git push
```

---

### Task 2: Keyword-matching module (HOH/Veto detection, no LLM)

**Files:**
- Create: `bb28_recap/keyword_match.py`
- Create: `tests/test_keyword_match.py`

**Interfaces:**
- Consumes: `models.RawPost`, `models.Fact` (existing).
- Produces: `keyword_match.match_hoh_veto_facts(posts: list[RawPost], housemate_names: list[str]) -> list[Fact]` — consumed by Task 4 (the 15-minute local script).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_keyword_match.py`:

```python
from datetime import datetime, timezone

from bb28_recap.keyword_match import match_hoh_veto_facts
from bb28_recap.models import RawPost


def _post(text):
    return RawPost(
        source="rss:test", text=text, published_at=datetime(2026, 7, 10, tzinfo=timezone.utc)
    )


def test_matches_hoh_when_name_and_hoh_keyword_present():
    posts = [_post("Alex wins HOH in dramatic competition")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert len(facts) == 1
    assert facts[0].fact_type == "status"
    assert facts[0].housemate == "Alex"
    assert facts[0].status == "HOH"
    assert facts[0].sources == ["rss:test"]


def test_matches_veto_when_name_and_veto_keyword_present():
    posts = [_post("Jordan wins veto competition")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert len(facts) == 1
    assert facts[0].housemate == "Jordan"
    assert facts[0].status == "Veto Winner"


def test_no_match_when_name_absent():
    posts = [_post("Someone wins HOH today")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert facts == []


def test_no_match_when_keyword_absent():
    posts = [_post("Alex talks strategy in the diary room")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert facts == []


def test_case_insensitive_matching():
    posts = [_post("ALEX WINS HOH")]
    facts = match_hoh_veto_facts(posts, ["alex"])
    assert len(facts) == 1
    assert facts[0].status == "HOH"


def test_multiple_housemates_in_one_post_only_matches_the_actor():
    posts = [_post("Alex wins HOH, nominates Jordan and Sam")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan", "Sam"])
    assert len(facts) == 1
    assert facts[0].housemate == "Alex"


def test_hoh_keyword_wins_when_both_hoh_and_veto_keywords_present():
    posts = [_post("Alex wins HOH after winning veto last week")]
    facts = match_hoh_veto_facts(posts, ["Alex"])
    assert len(facts) == 1
    assert facts[0].status == "HOH"


def test_empty_posts_returns_empty():
    assert match_hoh_veto_facts([], ["Alex"]) == []


def test_empty_housemate_list_returns_empty():
    posts = [_post("Alex wins HOH")]
    assert match_hoh_veto_facts(posts, []) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_keyword_match.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bb28_recap.keyword_match'`

- [ ] **Step 3: Write the implementation**

Create `bb28_recap/keyword_match.py`:

```python
"""Fast, free (no LLM) HOH/Veto win detection from RSS post text.

Only ever produces HOH or Veto Winner facts - nominations, evictions,
have-not, and jury status always require the full Claude extraction pass
and must never be added to this module's keyword lists."""
from __future__ import annotations

from .models import Fact, RawPost

HOH_KEYWORDS = [
    "wins hoh",
    "wins head of household",
    "new head of household",
    "hoh winner",
    "is the new hoh",
    "wins the hoh competition",
]

VETO_KEYWORDS = [
    "wins veto",
    "wins power of veto",
    "wins pov",
    "veto winner",
    "pov winner",
    "wins the veto competition",
]


def match_hoh_veto_facts(posts: list[RawPost], housemate_names: list[str]) -> list[Fact]:
    facts = []
    for post in posts:
        text_lower = post.text.lower()
        for name in housemate_names:
            if name.lower() not in text_lower:
                continue
            if any(kw in text_lower for kw in HOH_KEYWORDS):
                facts.append(
                    Fact(fact_type="status", housemate=name, status="HOH", sources=[post.source])
                )
            elif any(kw in text_lower for kw in VETO_KEYWORDS):
                facts.append(
                    Fact(
                        fact_type="status",
                        housemate=name,
                        status="Veto Winner",
                        sources=[post.source],
                    )
                )
    return facts
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_keyword_match.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add bb28_recap/keyword_match.py tests/test_keyword_match.py
git commit -m "feat: add keyword-matching module for free HOH/Veto detection"
git push
```

---

### Task 3: De-duplication module (avoid re-pushing the same post every 15 minutes)

**Files:**
- Create: `bb28_recap/dedup.py`
- Create: `tests/test_dedup.py`

**Interfaces:**
- Consumes: `models.RawPost` (existing).
- Produces: `dedup.post_key(post: RawPost) -> str`, `dedup.filter_unseen_posts(posts: list[RawPost], seen_keys: set[str]) -> list[RawPost]` — consumed by Task 4 (the 15-minute local script).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_dedup.py`:

```python
from datetime import datetime, timezone

from bb28_recap.dedup import filter_unseen_posts, post_key
from bb28_recap.models import RawPost


def _post(text, source="rss:a"):
    return RawPost(
        source=source, text=text, published_at=datetime(2026, 7, 10, tzinfo=timezone.utc)
    )


def test_post_key_is_stable_for_same_source_and_text():
    assert post_key(_post("hello")) == post_key(_post("hello"))


def test_post_key_differs_for_different_text():
    assert post_key(_post("hello")) != post_key(_post("world"))


def test_post_key_differs_for_different_source():
    assert post_key(_post("hello", source="rss:a")) != post_key(_post("hello", source="rss:b"))


def test_filter_unseen_posts_excludes_seen_keys():
    seen = {post_key(_post("old news"))}
    posts = [_post("old news"), _post("new news")]
    result = filter_unseen_posts(posts, seen)
    assert [p.text for p in result] == ["new news"]


def test_filter_unseen_posts_empty_seen_returns_all():
    posts = [_post("a"), _post("b")]
    assert filter_unseen_posts(posts, set()) == posts


def test_filter_unseen_posts_empty_posts_returns_empty():
    assert filter_unseen_posts([], {"x"}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bb28_recap.dedup'`

- [ ] **Step 3: Write the implementation**

Create `bb28_recap/dedup.py`:

```python
"""Track which posts have already been processed, so a still-recent post
sitting in the 24h RSS window doesn't get re-matched/re-pushed every run."""
from __future__ import annotations

from .models import RawPost


def post_key(post: RawPost) -> str:
    return f"{post.source}|{post.text}"


def filter_unseen_posts(posts: list[RawPost], seen_keys: set[str]) -> list[RawPost]:
    return [p for p in posts if post_key(p) not in seen_keys]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add bb28_recap/dedup.py tests/test_dedup.py
git commit -m "feat: add dedup module - track already-processed RSS posts"
git push
```

---

### Task 4: 15-minute local keyword-sync script

**Files:**
- Create: `local/keyword_sync.py`
- Create: `local/housemates.example.txt`
- Modify: `.gitignore`

**No automated tests for this task** — it's glue code that reads local files and makes a real HTTP call to HA; it reuses only already-tested functions from Tasks 2-3 and the existing `bb28_recap.aggregate`/`bb28_recap.sources_rss`/`bb28_recap.ha_push` modules. Verify with `python -m py_compile` and a manual run (Step 5 below).

**Interfaces:**
- Consumes: `aggregate.aggregate_sources` (existing), `sources_rss.fetch_rss_source` (existing), `config.RSS_FEEDS` (existing), `dedup.filter_unseen_posts`, `dedup.post_key` (Task 3), `keyword_match.match_hoh_veto_facts` (Task 2), `ha_push.build_ha_service_calls`, `ha_push.push_service_calls` (existing).

- [ ] **Step 1: Add `.gitignore` entries**

Modify `.gitignore` — add these lines (read the current file first to see exact existing content and append without duplicating):

```
local/.env
local/housemates.txt
local/keyword_seen.json
```

- [ ] **Step 2: Create the housemate roster template**

Create `local/housemates.example.txt`:

```
# One housemate name per line. Blank lines and lines starting with # are ignored.
# Copy this file to housemates.txt (gitignored) and fill in real names once
# the cast is revealed (8/7) - add new names here as add_housemate is called
# in Home Assistant, so the keyword matcher knows who to look for.
```

- [ ] **Step 3: Write `local/keyword_sync.py`**

```python
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
```

- [ ] **Step 4: Compile-check**

Run: `python -m py_compile local/keyword_sync.py`
Expected: no output, exit code 0

- [ ] **Step 5: Manual verification checklist (document, don't skip)**

This step is documentation of what to verify once real secrets exist — it cannot be automated here:

- [ ] Copy `local/housemates.example.txt` to `local/housemates.txt`, add a couple of real names.
- [ ] Create `local/.env` with `HA_BASE_URL` and `HA_LONG_LIVED_TOKEN`.
- [ ] Run `python local/keyword_sync.py` once manually — confirm it prints either "No HOH/Veto keyword matches this run." or a list of pushed facts, without crashing.
- [ ] Confirm `local/keyword_seen.json` gets created/updated after the run.
- [ ] Run it a second time immediately — confirm no facts get re-pushed for posts already seen (dedup working).

- [ ] **Step 6: Commit**

```bash
git add local/keyword_sync.py local/housemates.example.txt .gitignore
git commit -m "feat: add 15-min local keyword-sync script for free HOH/Veto HA updates"
git push
```

---

### Task 5: 8-hour local Claude-verification script

**Files:**
- Create: `local/claude_verify_sync.py`

**No automated tests for this task** — same reasoning as Task 4: pure glue reusing already-tested modules plus real Anthropic/HA clients. Verify with `python -m py_compile` and a manual run (Step 3 below).

**Interfaces:**
- Consumes: `aggregate.aggregate_sources`, `aggregate.render_raw_feed_text` (existing), `sources_rss.fetch_rss_source`, `config.RSS_FEEDS` (existing), `extract.EXTRACTION_SYSTEM_PROMPT`, `extract.build_extraction_prompt`, `extract.parse_extraction_response` (existing), `claude_response.extract_text_from_response` (Task 1), `ha_push.build_ha_service_calls`, `ha_push.push_service_calls` (existing).

- [ ] **Step 1: Write `local/claude_verify_sync.py`**

```python
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
```

- [ ] **Step 2: Compile-check**

Run: `python -m py_compile local/claude_verify_sync.py`
Expected: no output, exit code 0

- [ ] **Step 3: Manual verification checklist (document, don't skip)**

- [ ] Add `ANTHROPIC_API_KEY` to `local/.env` alongside the HA vars from Task 4.
- [ ] Run `python local/claude_verify_sync.py` once manually — confirm it prints either "No facts extracted this run." or a list of pushed facts, without crashing.
- [ ] Check the actual Anthropic usage dashboard shows one call was made (sanity-check cost is as expected, roughly a few cents).

- [ ] **Step 4: Commit**

```bash
git add local/claude_verify_sync.py
git commit -m "feat: add 8-hour local Claude-verification script for HA sync"
git push
```

---

### Task 6: Local secrets template, dependency, Task Scheduler docs, release

**Files:**
- Create: `local/.env.example`
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Add the `.env` template**

Create `local/.env.example`:

```
HA_BASE_URL=https://your-ha-instance.example.com
HA_LONG_LIVED_TOKEN=your-long-lived-token-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

- [ ] **Step 2: Add `python-dotenv` as a dependency**

Read `requirements.txt` first. Add a new line (check what version of `python-dotenv` is actually installed via `pip show python-dotenv` after `pip install python-dotenv`, and pin to that exact version, matching this project's existing pinned-dependency convention):

```
python-dotenv==<installed version>
```

Read `pyproject.toml` first. Add `"python-dotenv==<installed version>"` to the `dependencies` list in the `[project]` table, matching the existing entries' format.

- [ ] **Step 3: Add Task Scheduler setup docs to README**

Read the current `README.md` first. Append a new section after the existing "Manual smoke test" section:

```markdown
## Local HA sync (more frequent than the daily email)

Two optional local scripts push HA sensor updates far more often than the
once-daily Vercel cron, without needing Vercel's cron-frequency limits or
paying for extra Claude calls on every run:

- `local/keyword_sync.py` — every 15 min, free, keyword-matches RSS titles
  for HOH/Veto wins only (no Claude call).
- `local/claude_verify_sync.py` — every 8 hours, runs the full Claude
  extraction pass (nominations, evictions, have-not, jury, and anything the
  keyword pass missed).

### Setup

1. `pip install -r requirements.txt` (installs `python-dotenv` alongside the
   rest).
2. Copy `local/.env.example` to `local/.env` and fill in `HA_BASE_URL`,
   `HA_LONG_LIVED_TOKEN`, and `ANTHROPIC_API_KEY`.
3. Copy `local/housemates.example.txt` to `local/housemates.txt` and add
   real housemate names as they're revealed / added via the HA
   `add_housemate` service.
4. Schedule both scripts with Windows Task Scheduler (run from an elevated
   PowerShell or Command Prompt, replacing the path with your actual repo
   location):

```
schtasks /create /tn "BB28 Keyword Sync" /tr "python C:\path\to\bb28-daily-recap\local\keyword_sync.py" /sc minute /mo 15
schtasks /create /tn "BB28 Claude Verify Sync" /tr "python C:\path\to\bb28-daily-recap\local\claude_verify_sync.py" /sc hourly /mo 8
```

5. Test each manually first: `python local/keyword_sync.py` and
   `python local/claude_verify_sync.py` — both should run without errors
   before relying on the scheduled tasks.
```

- [ ] **Step 4: Run the full test suite one more time**

Run: `python -m pytest tests/ -v`
Expected: all tests pass (55 from Tasks 1-3, unchanged by Tasks 4-6 since those added no new automated tests)

Run: `python -m py_compile api/daily_recap.py bb28_recap/*.py local/*.py`
Expected: no output, exit code 0

- [ ] **Step 5: Commit, push, tag release**

```bash
git add local/.env.example requirements.txt pyproject.toml README.md
git commit -m "docs: add local HA sync setup - .env template, dependency, Task Scheduler commands"
git push
gh release create v1.2.0 --title "v1.2.0" --notes "Adds two optional local scripts for more frequent HA updates: a free 15-min keyword-matching pass for HOH/Veto wins (local/keyword_sync.py), and an 8-hour Claude-verification pass for everything else (local/claude_verify_sync.py). Both run via Windows Task Scheduler, independent of the daily Vercel email cron. See README for setup."
```
