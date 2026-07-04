from bb28_recap.email_content import (
    build_email_content,
    render_applied_updates,
    render_source_warnings,
)
from bb28_recap.models import HAServiceCall, PushResult


def test_render_applied_updates_formats_status_update():
    results = [
        PushResult(
            call=HAServiceCall(
                domain="big_brother_28",
                service="set_housemate_status",
                data={"name": "Alex", "status": "HOH"},
            ),
            success=True,
        )
    ]
    text = render_applied_updates(results)
    assert text == "Auto-updated: Alex → HOH"


def test_render_applied_updates_skips_failed_pushes():
    results = [
        PushResult(
            call=HAServiceCall(
                domain="big_brother_28",
                service="set_housemate_status",
                data={"name": "Alex", "status": "HOH"},
            ),
            success=False,
            error="HTTP 500",
        )
    ]
    assert render_applied_updates(results) == "No sensor updates applied today."


def test_render_applied_updates_empty_list():
    assert render_applied_updates([]) == "No sensor updates applied today."


def test_render_source_warnings_empty_when_no_missing_sources():
    assert render_source_warnings([]) == ""


def test_render_source_warnings_lists_each_missing_source():
    text = render_source_warnings(["x:a", "rss:b"])
    assert "x:a" in text
    assert "rss:b" in text
    assert "possible scrape break" in text


def test_build_email_content_subject_includes_day_number():
    content = build_email_content(5, "outline text", [], [])
    assert content.subject == "BB28 Daily Recap — Day 5"


def test_build_email_content_body_includes_outline_and_updates():
    results = [
        PushResult(
            call=HAServiceCall(
                domain="big_brother_28",
                service="set_housemate_status",
                data={"name": "Alex", "status": "HOH"},
            ),
            success=True,
        )
    ]
    content = build_email_content(5, "outline text here", results, [])
    assert "outline text here" in content.body
    assert "Auto-updated: Alex → HOH" in content.body


def test_build_email_content_body_includes_warnings_when_present():
    content = build_email_content(5, "outline", [], ["x:a"])
    assert "x:a" in content.body
    assert "possible scrape break" in content.body
