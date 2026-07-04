"""Build the daily talking-points-outline prompt for Claude."""
from __future__ import annotations

from .models import Fact

SUMMARY_SYSTEM_PROMPT = (
    "You are writing a talking-points outline for a Big Brother fan podcast host "
    "to read from during a 60+ minute livestream. Structure it into these segments: "
    "Overnight Recap, HOH and Nominations, Veto, Showmances, House Drama, "
    "Predictions and Wrap-up. Each segment should have enough bullet points to "
    "sustain several minutes of commentary. Write bullet points, not a word-for-word "
    "script - the host will speak naturally from them."
)


def render_facts_text(facts: list[Fact]) -> str:
    if not facts:
        return "(no clearly-confirmed facts today)"
    lines = []
    for fact in facts:
        if fact.fact_type == "status":
            lines.append(f"- {fact.housemate}: {fact.status} (sources: {', '.join(fact.sources)})")
        else:
            lines.append(
                f"- {fact.housemate}: {fact.fact_type}={fact.value} "
                f"(sources: {', '.join(fact.sources)})"
            )
    return "\n".join(lines)


def build_summary_prompt(raw_feed_text: str, facts_text: str) -> str:
    return (
        "Today's raw live-feed update text:\n\n"
        f"{raw_feed_text}\n\n"
        "Confirmed facts extracted from today's feed:\n\n"
        f"{facts_text}\n\n"
        "Write today's talking-points outline per your instructions."
    )
