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
