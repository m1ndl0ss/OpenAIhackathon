"""Regression checks for the draft boundary and fixture/live handoff."""

import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from backend import brane_client, integrations
from backend.agent.packets import calculate_capacity
from backend.agent.runtime import ModelTurn
from backend.store import snapshot
from tools.agent_utility import evaluate


def prepare(case, mode="fixture", authorize=lambda: None):
    return integrations.prepare_packets(case, mode, run_id="RUN-TEST", authorize=authorize)


@pytest.fixture
def configured_live(monkeypatch):
    monkeypatch.setenv("BRANE_API_KEY", "fixture-secret")
    monkeypatch.setenv("BRANE_BASE_URL", "https://assigned.example/api/v1")
    monkeypatch.setenv("BRANE_POLICY_VERSION", "hardened-v1")
    monkeypatch.setenv("BRANE_MODEL", "fixture-assigned-model")


@pytest.mark.parametrize(
    ("fixture", "status", "blocker", "after"),
    [
        ("LC-DEMO-001", "within_limit", None, 50_000_000),
        ("LC-INSUFFICIENT", "insufficient", "insufficient_headroom", -50_000_000),
        ("LC-EXPIRED-FACILITY", "unknown", "expired", None),
        ("LC-INVALID-FACILITY", "unknown", "invalid_amounts", None),
    ],
)
def test_capacity_and_packet_agree(fixture, status, blocker, after):
    case = snapshot("LC-001", "ORG_DEMO_01", fixture_id=fixture)
    capacity = calculate_capacity(case)
    assert (capacity.status, capacity.blocker, capacity.after_minor) == (status, blocker, after)
    assert capacity.source_ref == "FAC-USD-01@1"
    result = prepare(case)
    assert result.status == "prepared" and result.tool_reads == 8
    credit = result.packets["credit_risk"]
    if after is None:
        assert credit["missing_items"] == ["facility_snapshot"] and credit["facts"] == []
    else:
        assert {fact["field"]: fact["value"] for fact in credit["facts"]} == {
            "headroom_before_minor": 250_000_000, "headroom_after_minor": after
        }


def test_initial_and_amended_fixture_meet_answer_key():
    report = evaluate("fixture")
    assert (report["passed"], report["total"]) == (2, 2)
    initial, amended = report["runs"]
    assert initial["observed"]["owner"] == "coverage"
    assert amended["observed"]["missing"] == []
    assert initial["actual_total_tokens"] is None


def test_live_calls_receive_only_their_desk_context(monkeypatch, configured_live):
    seen = []

    def send(**turn):
        case_payload = json.loads(turn["messages"][1]["content"])
        seen.append((turn, case_payload))
        return ModelTurn("local", json.dumps({"summary": case_payload["wordings"][1]}), {
            "usage": {"total_tokens": 20}, "provider_request_id": "provider-demo",
        })

    monkeypatch.setattr(brane_client, "send_turn", send)
    result = prepare(snapshot("LC-001", "ORG_DEMO_01"), "live")
    assert result.status == "prepared" and result.policy_version == "hardened-v1"
    assert result.model_calls == len(seen) == 3
    for turn, context in seen:
        assert turn["case_ref"] == "LC-001" and turn["tool_schema"] == ()
        assert set(context) == {"desk", "next_step", "wordings"}
        assert turn["task"] == "draft_" + context["desk"]
        assert len(context["wordings"]) == 2
        for private_value in ("LC-001", "FAC-USD-01", "ORG_DEMO", "SCREEN-", "DOC-INV-", "2027-", "00000"):
            assert private_value not in json.dumps(turn["messages"])
        assert turn["timeout"] <= 60


@pytest.mark.parametrize("invalid", ["amount", "source", "text", "owner", "extra", "duplicate"])
def test_invalid_model_output_never_yields_a_bundle(monkeypatch, configured_live, invalid):
    def send(**turn):
        packet = {"summary": json.loads(turn["messages"][1]["content"])["wordings"][0]}
        if invalid == "amount":
            packet["facts"] = [{"field": "amount_minor", "value": 1}]
        elif invalid == "source":
            packet["evidence_refs"] = ["SCREEN-01@1"]
        elif invalid == "text":
            packet["summary"] = "Approved with unsupported information."
        elif invalid == "owner":
            packet["suggested_next_step"] = "request_operations"
        elif invalid == "extra":
            packet["signature"] = "approve"
        data = json.dumps(packet)
        if invalid == "duplicate":
            data = '{"summary":"other",' + data[1:]
        return ModelTurn("direct", data)

    monkeypatch.setattr(brane_client, "send_turn", send)
    result = prepare(snapshot("LC-001", "ORG_DEMO_01"), "live")
    assert result.status == "analysis_invalid" and result.packets is None and result.model_calls == 1


@pytest.mark.parametrize(
    ("route", "transient", "status", "attempts"),
    [("blocked", False, "analysis_refused", 1), ("unavailable", True, "analysis_unavailable", 2)],
)
def test_refusal_or_outage_never_falls_back(monkeypatch, configured_live, route, transient, status, attempts):
    monkeypatch.setattr(brane_client, "send_turn", lambda **_: ModelTurn(route, transient=transient))
    result = prepare(snapshot("LC-001", "ORG_DEMO_01"), "live")
    assert result.status == status and result.model_calls == attempts and result.packets is None


def test_unassigned_case_cannot_read_or_draft(monkeypatch, configured_live):
    def denied():
        raise PermissionError("Outside assigned case")

    def must_not_send(**_):
        pytest.fail("Unassigned case attempted a model call")

    monkeypatch.setattr(brane_client, "send_turn", must_not_send)
    result = prepare(snapshot("LC-OTHER", "ORG_OTHER"), "live", denied)
    assert result.packets is None and result.model_calls == 0


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"X-Brane-Routed-To": "cloud", "X-Brane-Action": "allow"}, "direct"),
        ({"X-Brane-Routed-To": "cloud", "X-Brane-Action": "placeholder", "X-Brane-Redacted": "true"}, "pseudonymized"),
        ({"X-Brane-Routed-To": "local", "X-Brane-Action": "local"}, "local"),
        ({"X-Brane-Routed-To": "cloud", "X-Brane-Action": "placeholder"}, "unavailable"),
        ({"X-Brane-Routed-To": "cloud", "X-Brane-Action": "allow", "X-Brane-Policy-Version": "baseline"}, "unavailable"),
        ({}, "unavailable"),
    ],
)
def test_http_adapter_requires_observable_route(monkeypatch, configured_live, headers, expected):
    class Response(BytesIO):
        status = 200

    response = Response(b'{"choices":[{"message":{"content":"{}"}}],"usage":{"total_tokens":3}}')
    response.headers = headers

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "https://assigned.example/api/v1/chat/completions"
            assert json.loads(request.data)["model"] == "fixture-assigned-model"
            assert timeout <= 15
            return response

    monkeypatch.setattr(brane_client, "build_opener", lambda *_: Opener())
    result = brane_client.send_turn(case_ref="LC-001", revision=1, run_id="RUN-TEST", task="draft_trade_finance",
                                    policy_version="hardened-v1", messages=[], tool_schema=(), timeout=60)
    assert result.route == expected
    if expected != "unavailable":
        assert result.observation["usage"]["total_tokens"] == 3


def test_http_refusal_never_reads_error_body(monkeypatch, configured_live):
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 422, "Refused", {"X-Brane-Action": "refuse"}, BytesIO(b"RAW"))

    monkeypatch.setattr(brane_client, "build_opener", lambda *_: Opener())
    result = brane_client.send_turn(case_ref="LC-001", revision=1, run_id="RUN-TEST", task="draft_trade_finance",
                                    policy_version="hardened-v1", messages=[], tool_schema=(), timeout=60)
    assert result.route == "blocked" and result.completion is None
