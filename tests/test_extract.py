import json

import pytest

from bb28_recap.extract import (
    InvalidExtractionResponseError,
    build_extraction_prompt,
    parse_extraction_response,
)


def test_build_extraction_prompt_includes_raw_feed_text():
    prompt = build_extraction_prompt("[09:00] (x:a) Alex won HOH")
    assert "Alex won HOH" in prompt


def test_parse_extraction_response_parses_status_fact():
    response = json.dumps(
        [{"housemate": "Alex", "fact_type": "status", "status": "HOH", "sources": ["x:a"]}]
    )
    facts = parse_extraction_response(response)
    assert len(facts) == 1
    assert facts[0].housemate == "Alex"
    assert facts[0].fact_type == "status"
    assert facts[0].status == "HOH"
    assert facts[0].sources == ["x:a"]


def test_parse_extraction_response_parses_have_not_fact():
    response = json.dumps(
        [{"housemate": "Jordan", "fact_type": "have_not", "value": True, "sources": ["rss:b"]}]
    )
    facts = parse_extraction_response(response)
    assert facts[0].fact_type == "have_not"
    assert facts[0].value is True


def test_parse_extraction_response_parses_jury_fact():
    response = json.dumps(
        [{"housemate": "Sam", "fact_type": "jury", "value": True, "sources": ["x:a"]}]
    )
    facts = parse_extraction_response(response)
    assert facts[0].fact_type == "jury"
    assert facts[0].value is True


def test_parse_extraction_response_empty_array_returns_empty_list():
    assert parse_extraction_response("[]") == []


def test_parse_extraction_response_raises_on_invalid_json():
    with pytest.raises(InvalidExtractionResponseError):
        parse_extraction_response("not json")


def test_parse_extraction_response_raises_on_non_array():
    with pytest.raises(InvalidExtractionResponseError):
        parse_extraction_response(json.dumps({"not": "a list"}))


def test_parse_extraction_response_raises_on_unknown_fact_type():
    response = json.dumps([{"housemate": "Alex", "fact_type": "bogus"}])
    with pytest.raises(InvalidExtractionResponseError):
        parse_extraction_response(response)
