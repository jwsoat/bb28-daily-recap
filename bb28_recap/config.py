"""Config, constants, and the pure day-number computation for BB28 daily recap."""
from __future__ import annotations

from datetime import date

BB28_START_DATE = "2026-07-09"
BB28_TIMEZONE = "America/Los_Angeles"
RECIPIENT_EMAIL = "info@jwsoat.com"

X_ACCOUNTS = [
    "TheBigBroTea",
    "hamsterwatch",
    "89razorskate20",
    "BBFeedsFairy",
    "rbbq",
    "bigbrothernet",
    "BBigBrotherBuzz",
]

RSS_FEEDS = [
    "https://bigbrothernetwork.com/feed/",
    "https://bigbrotherus.com/feed/",
    "https://www.onlinebigbrother.com/feed/",
]

REQUIRED_ENV_VARS = [
    "X_BURNER_USERNAME",
    "X_BURNER_PASSWORD",
    "X_BURNER_EMAIL",
    "ANTHROPIC_API_KEY",
    "RESEND_API_KEY",
    "HA_BASE_URL",
    "HA_LONG_LIVED_TOKEN",
]


class MissingEnvVarError(RuntimeError):
    pass


def load_env_config(env: dict) -> dict:
    """Validate all required secrets are present; return them as a plain dict."""
    missing = [name for name in REQUIRED_ENV_VARS if not env.get(name)]
    if missing:
        raise MissingEnvVarError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )
    return {name: env[name] for name in REQUIRED_ENV_VARS}


def compute_day_number(today: date, start_date_str: str = BB28_START_DATE) -> int:
    """Day 1 = start_date. Returns 0 if today is before start_date."""
    start = date.fromisoformat(start_date_str)
    delta = (today - start).days + 1
    return max(delta, 0)
