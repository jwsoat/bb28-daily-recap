from datetime import datetime, timezone

from bb28_recap.keyword_match import match_hoh_veto_facts
from bb28_recap.models import RawPost


def _post(text):
    return RawPost(
        source="rss:test", text=text, published_at=datetime(2026, 7, 10, tzinfo=timezone.utc)
    )


def test_matches_hoh_when_name_and_hoh_keyword_present():
    posts = [_post("Alex wins HOH in dramatic competition")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": []})
    assert len(facts) == 1
    assert facts[0].fact_type == "status"
    assert facts[0].housemate == "Alex"
    assert facts[0].status == "HOH"
    assert facts[0].sources == ["rss:test"]


def test_matches_veto_when_name_and_veto_keyword_present():
    posts = [_post("Jordan wins veto competition")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": []})
    assert len(facts) == 1
    assert facts[0].housemate == "Jordan"
    assert facts[0].status == "Veto Winner"


def test_no_match_when_name_absent():
    posts = [_post("Someone wins HOH today")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": []})
    assert facts == []


def test_no_match_when_keyword_absent():
    posts = [_post("Alex talks strategy in the diary room")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": []})
    assert facts == []


def test_case_insensitive_matching():
    posts = [_post("ALEX WINS HOH")]
    facts = match_hoh_veto_facts(posts, {"alex": []})
    assert len(facts) == 1
    assert facts[0].status == "HOH"


def test_multiple_housemates_in_one_post_only_matches_the_actor():
    posts = [_post("Alex wins HOH, nominates Jordan and Sam")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": [], "Sam": []})
    assert len(facts) == 1
    assert facts[0].housemate == "Alex"


def test_hoh_keyword_wins_when_both_hoh_and_veto_keywords_present():
    posts = [_post("Alex wins HOH after winning veto last week")]
    facts = match_hoh_veto_facts(posts, {"Alex": []})
    assert len(facts) == 1
    assert facts[0].status == "HOH"


def test_empty_posts_returns_empty():
    assert match_hoh_veto_facts([], {"Alex": []}) == []


def test_empty_housemate_dict_returns_empty():
    posts = [_post("Alex wins HOH")]
    assert match_hoh_veto_facts(posts, {}) == []


def test_matches_hoh_when_keyword_comes_before_name():
    posts = [_post("HOH Winner: Alex")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": []})
    assert len(facts) == 1
    assert facts[0].housemate == "Alex"
    assert facts[0].status == "HOH"


def test_matches_veto_when_keyword_comes_before_name():
    posts = [_post("Veto Winner: Jordan")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": []})
    assert len(facts) == 1
    assert facts[0].housemate == "Jordan"
    assert facts[0].status == "Veto Winner"


def test_matches_hoh_winner_phrase_with_name_after():
    posts = [_post("New Head of Household: Alex Smith")]
    facts = match_hoh_veto_facts(posts, {"Alex": ["Alex Smith"], "Jordan": []})
    assert len(facts) == 1
    assert facts[0].housemate == "Alex"
    assert facts[0].status == "HOH"


def test_keyword_before_name_picks_closest_name_when_multiple_present():
    posts = [_post("HOH Winner: Alex (Jordan and Sam were also nominated)")]
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": [], "Sam": []})
    assert len(facts) == 1
    assert facts[0].housemate == "Alex"
    assert facts[0].status == "HOH"


def test_hoh_in_one_post_does_not_suppress_veto_in_a_different_post_same_source():
    posts = [
        _post("Alex wins HOH in dramatic competition"),
        _post("Jordan wins veto competition"),
    ]
    # both posts use the same default source ("rss:test") from the _post helper
    facts = match_hoh_veto_facts(posts, {"Alex": [], "Jordan": []})
    assert len(facts) == 2
    statuses = {f.housemate: f.status for f in facts}
    assert statuses == {"Alex": "HOH", "Jordan": "Veto Winner"}


def test_matches_via_alias_and_attributes_to_canonical_name():
    # "K-Dog" shares no substring with "Kamu" - this only passes if the alias
    # list is actually searched, not by accidental substring overlap.
    posts = [_post("K-Dog wins HOH")]
    facts = match_hoh_veto_facts(posts, {"Kamu": ["K-Dog"]})
    assert len(facts) == 1
    assert facts[0].housemate == "Kamu"
    assert facts[0].status == "HOH"


def test_matches_via_full_name_alias_not_just_canonical_first_name():
    # "robin" is not a substring of "robertson" (compare: robin vs rob-e-rtson)
    posts = [_post("Robertson Payne wins veto")]
    facts = match_hoh_veto_facts(posts, {"Robin": ["Robertson Payne"], "Jordan": []})
    assert len(facts) == 1
    assert facts[0].housemate == "Robin"
    assert facts[0].status == "Veto Winner"


def test_alias_closest_to_keyword_disambiguates_between_two_people():
    posts = [_post("HOH Winner: K-Dog (Robertson Payne was also nominated)")]
    facts = match_hoh_veto_facts(
        posts, {"Kamu": ["K-Dog"], "Robin": ["Robertson Payne"]}
    )
    assert len(facts) == 1
    assert facts[0].housemate == "Kamu"


def test_canonical_name_itself_still_matches_when_aliases_present():
    posts = [_post("Kamu wins veto")]
    facts = match_hoh_veto_facts(posts, {"Kamu": ["Kamuela", "Kamuela Kirk"]})
    assert len(facts) == 1
    assert facts[0].housemate == "Kamu"
    assert facts[0].status == "Veto Winner"
