import asyncio

from bb28_recap.ha_push import build_add_housemate_calls, build_ha_service_calls, push_service_calls
from bb28_recap.models import Fact, HAServiceCall


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeSession:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    async def post(self, url, json, headers):
        self.calls.append((url, json, headers))
        result = self._responses[len(self.calls) - 1]
        if isinstance(result, Exception):
            raise result
        return FakeResponse(status_code=result)


def test_build_ha_service_calls_maps_status_fact():
    facts = [Fact(fact_type="status", housemate="Alex", status="HOH", sources=["x:a"])]
    calls = build_ha_service_calls(facts)
    assert calls == [
        HAServiceCall(
            domain="big_brother_28",
            service="set_housemate_status",
            data={"name": "Alex", "status": "HOH"},
        )
    ]


def test_build_ha_service_calls_maps_have_not_fact():
    facts = [Fact(fact_type="have_not", housemate="Jordan", value=True)]
    calls = build_ha_service_calls(facts)
    assert calls == [
        HAServiceCall(
            domain="big_brother_28",
            service="set_have_not",
            data={"name": "Jordan", "is_have_not": True},
        )
    ]


def test_build_ha_service_calls_maps_jury_as_status_fact():
    facts = [Fact(fact_type="status", housemate="Sam", status="Jury", sources=["x:a"])]
    calls = build_ha_service_calls(facts)
    assert calls == [
        HAServiceCall(
            domain="big_brother_28",
            service="set_housemate_status",
            data={"name": "Sam", "status": "Jury"},
        )
    ]


def test_build_add_housemate_calls_maps_each_name():
    calls = build_add_housemate_calls(["Alex", "Jordan"])
    assert calls == [
        HAServiceCall(domain="big_brother_28", service="add_housemate", data={"name": "Alex"}),
        HAServiceCall(domain="big_brother_28", service="add_housemate", data={"name": "Jordan"}),
    ]


def test_build_add_housemate_calls_empty_list_returns_empty():
    assert build_add_housemate_calls([]) == []


def test_push_service_calls_reports_success():
    calls = [HAServiceCall(domain="big_brother_28", service="set_housemate_status", data={})]
    session = FakeSession([200])
    results = asyncio.run(push_service_calls(session, "https://ha.example.com", "tok", calls))
    assert results[0].success is True
    assert results[0].error is None


def test_push_service_calls_reports_http_error_without_raising():
    calls = [HAServiceCall(domain="big_brother_28", service="set_housemate_status", data={})]
    session = FakeSession([500])
    results = asyncio.run(push_service_calls(session, "https://ha.example.com", "tok", calls))
    assert results[0].success is False
    assert "500" in results[0].error


def test_push_service_calls_isolates_a_raised_exception_per_call():
    calls = [
        HAServiceCall(domain="big_brother_28", service="set_housemate_status", data={}),
        HAServiceCall(domain="big_brother_28", service="set_have_not", data={}),
    ]
    session = FakeSession([ConnectionError("network down"), 200])
    results = asyncio.run(push_service_calls(session, "https://ha.example.com", "tok", calls))
    assert results[0].success is False
    assert "network down" in results[0].error
    assert results[1].success is True
