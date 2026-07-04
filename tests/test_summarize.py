from bb28_recap.models import Fact
from bb28_recap.summarize import build_summary_prompt, render_facts_text


def test_render_facts_text_formats_status_fact():
    facts = [Fact(fact_type="status", housemate="Alex", status="HOH", sources=["x:a"])]
    text = render_facts_text(facts)
    assert text == "- Alex: HOH (sources: x:a)"


def test_render_facts_text_formats_have_not_fact():
    facts = [Fact(fact_type="have_not", housemate="Jordan", value=True, sources=["rss:b"])]
    text = render_facts_text(facts)
    assert text == "- Jordan: have_not=True (sources: rss:b)"


def test_render_facts_text_handles_empty_list():
    assert render_facts_text([]) == "(no clearly-confirmed facts today)"


def test_build_summary_prompt_includes_both_blobs():
    prompt = build_summary_prompt("raw feed text here", "facts text here")
    assert "raw feed text here" in prompt
    assert "facts text here" in prompt
