# BB28 Daily Recap

Scrapes RSS for Big Brother 28 live-feed updates, extracts confirmed
game facts with Claude, pushes them into the `big_brother_28` Home Assistant
integration, and emails a 60+min talking-points outline before your livestream.

**X scraping is disabled for now (RSS-only).** The X integration (`bb28_recap/sources_x.py`)
is fully built and tested but not wired into `api/daily_recap.py` — see that file's
module docstring for how to re-enable it (restore the `TwikitXClient` wrapper,
add `twikit` back to `requirements.txt`, and re-add the 3 `X_BURNER_*` env vars
to `config.REQUIRED_ENV_VARS`).

Runs daily via Vercel Cron at 22:00 UTC (3pm PT).

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Create a Vercel project linked to this repo.
3. Set these environment variables in the Vercel dashboard (Production):
   - `ANTHROPIC_API_KEY`
   - `RESEND_API_KEY`
   - `HA_BASE_URL` — your Home Assistant instance's public URL (reverse proxy).
   - `HA_LONG_LIVED_TOKEN` — a long-lived access token from your HA profile page.
4. Deploy. The cron is defined in `vercel.json`.

## Tests

`pytest tests/ -v` — all business logic is pure and unit-tested. The Vercel
entry point (`api/daily_recap.py`) has no automated tests (it's the one place
real network clients get constructed) — verify it manually after deploying
with real secrets.

## Manual smoke test (run this after deploying with real secrets)

There is no automated test for `api/daily_recap.py` - it's the one place
real credentials and network calls happen. After deploying to Vercel with
all 4 env vars set:

1. Trigger the function manually: visit `https://<your-deployment>.vercel.app/api/daily_recap`
   in a browser, or `curl` it.
2. Check it returns `200 OK`.
3. Check `info@jwsoat.com` received an email within a minute or two.
4. Check the email's "Auto-updated" section against your actual HA sensors
   (Settings -> Devices & Services -> Big Brother 28) to confirm the push
   actually landed.
5. Check Vercel's function logs (Vercel dashboard -> your project -> Logs)
   for any warnings about missing sources or failed HA pushes.

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
