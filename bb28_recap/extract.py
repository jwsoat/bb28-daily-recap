"""Build the extraction prompt and parse Claude's structured JSON response."""
from __future__ import annotations

import json

from .models import Fact

EXTRACTION_SYSTEM_PROMPT = (
    "You are extracting confirmed Big Brother game facts from live-feed update posts. "
    "Only extract a fact if it is clearly and unambiguously stated as having happened - "
    "never guess, infer from jokes, or extract speculation/predictions. "
    "Return ONLY a JSON array, no other text. Each element must have exactly these keys: "
    '"housemate" (string), "fact_type" (one of "status", "have_not"), '
    '"status" (string, required when fact_type is "status", one of: HOH, Nominated, '
    'Veto Competitor, Veto Winner, Eliminated, Jury - omit for "have_not"), '
    '"value" (boolean, required when fact_type is "have_not" - omit for "status"), '
    '"sources" (array of strings - which source tags in the feed stated this fact). '
    "If no facts are clearly stated, return an empty array []."
)


def build_extraction_prompt(raw_feed_text: str) -> str:
    return (
        "Here is today's raw Big Brother live-feed update text, "
        "each line tagged with its source and time:\n\n"
        f"{raw_feed_text}\n\n"
        "Extract the confirmed facts as a JSON array per your instructions."
    )


class InvalidExtractionResponseError(ValueError):
    pass


def parse_extraction_response(response_text: str) -> list[Fact]:
    try:
        raw_facts = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise InvalidExtractionResponseError(
            f"Claude extraction response was not valid JSON: {exc}"
        ) from exc

    if not isinstance(raw_facts, list):
        raise InvalidExtractionResponseError("Claude extraction response was not a JSON array")

    facts = []
    for item in raw_facts:
        if not isinstance(item, dict):
            raise InvalidExtractionResponseError(
                f"Expected each array element to be an object, got: {item!r}"
            )
        fact_type = item.get("fact_type")
        if fact_type not in ("status", "have_not"):
            raise InvalidExtractionResponseError(f"Unknown fact_type: {fact_type!r}")
        facts.append(
            Fact(
                fact_type=fact_type,
                housemate=item.get("housemate", ""),
                status=item.get("status", ""),
                value=item.get("value"),
                sources=item.get("sources", []),
            )
        )
    return facts
