"""Compose the daily recap email's subject and body."""
from __future__ import annotations

from .models import EmailContent, PushResult


def render_applied_updates(push_results: list[PushResult]) -> str:
    lines = []
    for result in push_results:
        if not result.success:
            continue
        data = result.call.data
        if result.call.service == "set_housemate_status":
            lines.append(f"Auto-updated: {data['name']} → {data['status']}")
        elif result.call.service == "set_have_not":
            lines.append(f"Auto-updated: {data['name']} have-not → {data['is_have_not']}")
        elif result.call.service == "set_jury_status":
            lines.append(f"Auto-updated: {data['name']} jury → {data['is_jury_member']}")
    if not lines:
        return "No sensor updates applied today."
    return "\n".join(lines)


def render_source_warnings(missing_sources_list: list[str]) -> str:
    if not missing_sources_list:
        return ""
    warnings = [
        f"⚠ No fresh posts/entries found for {source} — possible scrape break"
        for source in missing_sources_list
    ]
    return "\n".join(warnings)


def build_email_content(
    day_number: int,
    outline: str,
    push_results: list[PushResult],
    missing_sources_list: list[str],
) -> EmailContent:
    subject = f"BB28 Daily Recap — Day {day_number}"
    sections = [outline, "", "---", "", render_applied_updates(push_results)]
    warnings_text = render_source_warnings(missing_sources_list)
    if warnings_text:
        sections += ["", warnings_text]
    body = "\n".join(sections)
    return EmailContent(subject=subject, body=body)
