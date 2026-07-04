# BB28 Daily Recap

Scrapes X + RSS for Big Brother 28 live-feed updates, extracts confirmed
game facts with Claude, pushes them into the `big_brother_28` Home Assistant
integration, and emails a 60+min talking-points outline before your livestream.

Runs daily via Vercel Cron at 22:00 UTC (3pm PT).

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Create a Vercel project linked to this repo.
3. Set these environment variables in the Vercel dashboard (Production):
   - `X_BURNER_USERNAME`, `X_BURNER_PASSWORD`, `X_BURNER_EMAIL` — a dedicated
     burner X account's login, not your personal account.
   - `ANTHROPIC_API_KEY`
   - `RESEND_API_KEY`
   - `HA_BASE_URL` — your Home Assistant instance's public URL (reverse proxy).
   - `HA_LONG_LIVED_TOKEN` — a long-lived access token from your HA profile page.
4. Deploy. The cron is defined in `vercel.json`.

## Tests

`pytest tests/ -v` — all business logic is pure and unit-tested. The Vercel
entry point (`api/daily-recap.py`) has no automated tests (it's the one place
real network clients get constructed) — verify it manually after deploying
with real secrets.

## Manual smoke test (run this after deploying with real secrets)

There is no automated test for `api/daily-recap.py` - it's the one place
real credentials and network calls happen. After deploying to Vercel with
all 7 env vars set:

1. Trigger the function manually: visit `https://<your-deployment>.vercel.app/api/daily-recap`
   in a browser, or `curl` it.
2. Check it returns `200 OK`.
3. Check `info@jwsoat.com` received an email within a minute or two.
4. Check the email's "Auto-updated" section against your actual HA sensors
   (Settings -> Devices & Services -> Big Brother 28) to confirm the push
   actually landed.
5. Check Vercel's function logs (Vercel dashboard -> your project -> Logs)
   for any warnings about missing sources or failed HA pushes.
6. If `twikit`'s login/tweet-fetch API doesn't match what's implemented in
   `api/daily-recap.py` (see the note in `TwikitXClient`), the logs will
   show the exact error - adjust the method calls there without touching
   any file under `bb28_recap/` (that's all covered by pytest already).
