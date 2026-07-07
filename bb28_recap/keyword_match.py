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

        # Check for HOH keywords first (HOH wins tie-break over Veto)
        for hoh_keyword in HOH_KEYWORDS:
            if hoh_keyword in text_lower:
                # Find which housemate appears before this keyword
                keyword_pos = text_lower.find(hoh_keyword)
                matching_name = None
                latest_name_pos = -1

                for name in housemate_names:
                    name_lower = name.lower()
                    name_pos = text_lower.find(name_lower)
                    # Check if name appears before the keyword and is the closest one
                    if name_pos != -1 and name_pos < keyword_pos and name_pos > latest_name_pos:
                        matching_name = name
                        latest_name_pos = name_pos

                if matching_name:
                    facts.append(
                        Fact(
                            fact_type="status",
                            housemate=matching_name,
                            status="HOH",
                            sources=[post.source],
                        )
                    )
                    break  # Only one HOH per post

        # Check for Veto keywords only if no HOH match was found
        if not any(f.status == "HOH" and f.sources == [post.source] for f in facts):
            for veto_keyword in VETO_KEYWORDS:
                if veto_keyword in text_lower:
                    # Find which housemate appears before this keyword
                    keyword_pos = text_lower.find(veto_keyword)
                    matching_name = None
                    latest_name_pos = -1

                    for name in housemate_names:
                        name_lower = name.lower()
                        name_pos = text_lower.find(name_lower)
                        # Check if name appears before the keyword and is the closest one
                        if name_pos != -1 and name_pos < keyword_pos and name_pos > latest_name_pos:
                            matching_name = name
                            latest_name_pos = name_pos

                    if matching_name:
                        facts.append(
                            Fact(
                                fact_type="status",
                                housemate=matching_name,
                                status="Veto Winner",
                                sources=[post.source],
                            )
                        )
                        break  # Only one Veto per post

    return facts
