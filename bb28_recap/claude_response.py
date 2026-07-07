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
