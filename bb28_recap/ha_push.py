"""Turn extracted facts into HA REST service-call payloads and push them."""
from __future__ import annotations

from .models import Fact, HAServiceCall, PushResult


def build_ha_service_calls(facts: list[Fact]) -> list[HAServiceCall]:
    calls = []
    for fact in facts:
        if fact.fact_type == "status":
            calls.append(
                HAServiceCall(
                    domain="big_brother_28",
                    service="set_housemate_status",
                    data={"name": fact.housemate, "status": fact.status},
                )
            )
        elif fact.fact_type == "have_not":
            calls.append(
                HAServiceCall(
                    domain="big_brother_28",
                    service="set_have_not",
                    data={"name": fact.housemate, "is_have_not": bool(fact.value)},
                )
            )
    return calls


def build_add_housemate_calls(names: list[str]) -> list[HAServiceCall]:
    """Idempotent - big_brother_28.add_housemate is a no-op if the housemate
    already exists, so this is safe to call on every run to keep HA's roster
    in sync with local/housemates.txt (e.g. after HA gets reinstalled)."""
    return [
        HAServiceCall(domain="big_brother_28", service="add_housemate", data={"name": name})
        for name in names
    ]


async def push_service_calls(
    session, base_url: str, token: str, calls: list[HAServiceCall]
) -> list[PushResult]:
    """session must expose an async post(url, json, headers) -> response with .status_code."""
    results = []
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for call in calls:
        url = f"{base_url}/api/services/{call.domain}/{call.service}"
        try:
            response = await session.post(url, json=call.data, headers=headers)
            if response.status_code >= 400:
                results.append(
                    PushResult(call=call, success=False, error=f"HTTP {response.status_code}")
                )
            else:
                results.append(PushResult(call=call, success=True))
        except Exception as exc:  # noqa: BLE001 - any per-call failure is isolated, not fatal
            results.append(PushResult(call=call, success=False, error=str(exc)))
    return results
