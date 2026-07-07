from datetime import datetime, timezone

from bb28_recap.keyword_match import match_hoh_veto_facts
from bb28_recap.models import RawPost


def _post(text):
    return RawPost(
        source="rss:test", text=text, published_at=datetime(2026, 7, 10, tzinfo=timezone.utc)
    )


def test_matches_hoh_when_name_and_hoh_keyword_present():
    posts = [_post("Alex wins HOH in dramatic competition")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert len(facts) == 1
    assert facts[0].fact_type == "status"
    assert facts[0].housemate == "Alex"
    assert facts[0].status == "HOH"
    assert facts[0].sources == ["rss:test"]


def test_matches_veto_when_name_and_veto_keyword_present():
    posts = [_post("Jordan wins veto competition")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert len(facts) == 1
    assert facts[0].housemate == "Jordan"
    assert facts[0].status == "Veto Winner"


def test_no_match_when_name_absent():
    posts = [_post("Someone wins HOH today")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert facts == []


def test_no_match_when_keyword_absent():
    posts = [_post("Alex talks strategy in the diary room")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan"])
    assert facts == []


def test_case_insensitive_matching():
    posts = [_post("ALEX WINS HOH")]
    facts = match_hoh_veto_facts(posts, ["alex"])
    assert len(facts) == 1
    assert facts[0].status == "HOH"


def test_multiple_housemates_in_one_post_only_matches_the_actor():
    posts = [_post("Alex wins HOH, nominates Jordan and Sam")]
    facts = match_hoh_veto_facts(posts, ["Alex", "Jordan", "Sam"])
    assert len(facts) == 1
    assert facts[0].housemate == "Alex"


def test_hoh_keyword_wins_when_both_hoh_and_veto_keywords_present():
    posts = [_post("Alex wins HOH after winning veto last week")]
    facts = match_hoh_veto_facts(posts, ["Alex"])
    assert len(facts) == 1
    assert facts[0].status == "HOH"


def test_empty_posts_returns_empty():
    assert match_hoh_veto_facts([], ["Alex"]) == []


def test_empty_housemate_list_returns_empty():
    posts = [_post("Alex wins HOH")]
    assert match_hoh_veto_facts(posts, []) == []
