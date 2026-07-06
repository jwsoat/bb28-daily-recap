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
