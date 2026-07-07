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


def _distance_for_alias(
    text_lower: str, alias: str, keyword_pos: int, keyword_len: int
) -> int | None:
    """Character distance (either direction) between an alias occurrence and
    a keyword match, or None if the alias doesn't appear in the text."""
    alias_lower = alias.lower()
    alias_pos = text_lower.find(alias_lower)
    if alias_pos == -1:
        return None

    if alias_pos < keyword_pos:
        distance = keyword_pos - (alias_pos + len(alias_lower))
    else:
        distance = alias_pos - (keyword_pos + keyword_len)
    return max(distance, 0)


def _closest_canonical_to_position(
    text_lower: str,
    keyword_pos: int,
    keyword_len: int,
    housemate_aliases: dict[str, list[str]],
) -> str | None:
    """Find whichever housemate has an occurrence (canonical name or any of
    their aliases) closest to a keyword match at keyword_pos."""
    best_canonical = None
    best_distance = None

    for canonical_name, aliases in housemate_aliases.items():
        person_best = None
        for name in [canonical_name, *aliases]:
            distance = _distance_for_alias(text_lower, name, keyword_pos, keyword_len)
            if distance is not None and (person_best is None or distance < person_best):
                person_best = distance

        if person_best is not None and (best_distance is None or person_best < best_distance):
            best_distance = person_best
            best_canonical = canonical_name

    return best_canonical


def match_hoh_veto_facts(
    posts: list[RawPost], housemate_aliases: dict[str, list[str]]
) -> list[Fact]:
    """housemate_aliases maps each housemate's canonical name (the name used
    for their HA sensor) to a list of extra name variants to search for in
    post text - nicknames, full legal names, etc. A match on the canonical
    name or any alias attributes the fact to the canonical name."""
    facts = []
    for post in posts:
        text_lower = post.text.lower()
        hoh_matched_this_post = False

        # Check for HOH keywords first (HOH wins tie-break over Veto)
        for hoh_keyword in HOH_KEYWORDS:
            if hoh_keyword in text_lower:
                keyword_pos = text_lower.find(hoh_keyword)
                matching_name = _closest_canonical_to_position(
                    text_lower, keyword_pos, len(hoh_keyword), housemate_aliases
                )

                if matching_name:
                    facts.append(
                        Fact(
                            fact_type="status",
                            housemate=matching_name,
                            status="HOH",
                            sources=[post.source],
                        )
                    )
                    hoh_matched_this_post = True
                break  # Only one HOH per post

        # Check for Veto keywords only if no HOH match was found in this post
        if not hoh_matched_this_post:
            for veto_keyword in VETO_KEYWORDS:
                if veto_keyword in text_lower:
                    keyword_pos = text_lower.find(veto_keyword)
                    matching_name = _closest_canonical_to_position(
                        text_lower, keyword_pos, len(veto_keyword), housemate_aliases
                    )

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
