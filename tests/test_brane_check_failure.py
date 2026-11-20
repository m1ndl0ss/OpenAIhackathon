import os

import pytest

from scripts import brane_client as transport, check_failure_test as harness


@pytest.mark.parametrize(("status", "headers", "expected"), [
    ("200", {"X-Brane-Routed-To": "cloud"}, "unavailable"),
    ("200", {"X-Brane-Routed-To": "cloud", "X-Brane-Action": "placeholder",
             "X-Brane-Redacted": "true"}, "unavailable"),
    ("422", {}, "unavailable"),
    ("422", {"X-Brane-Routed-To": "refused", "X-Brane-Action": "refuse"}, "blocked"),
    ("200", {"X-Brane-Routed-To": "cloud", "X-Brane-Action": "allow", "X-Brane-Redacted": "false"}, "direct"),
])
def test_governed_reply_requires_a_complete_verdict(monkeypatch, status, headers, expected):
    completion = "Synthetic review draft"
    body = {"choices": [{"message": {"content": completion}}]}
    monkeypatch.setattr(transport, "request", lambda *args, **kwargs: (status, headers, body, ""))
    result = transport.call_governed("Synthetic desk review")
    assert result["outcome"] == expected
    assert result["answer"] == (completion if expected == "direct" else None)


def test_fault_credentials_and_exact_url_are_isolated(monkeypatch):
    base = transport.ASSIGNED_BASE
    monkeypatch.setenv("BRANE_BASE_URL", base)
    for key in ("BRANE_API_KEY", "BRANE_TOKEN"):
        monkeypatch.setenv(key, "synthetic-control-credential")
    during = []

    def observe(_prompt, timeout):
        during.append((transport.base_url(), transport.api_key(), os.environ["BRANE_TOKEN"]))
        return {"outcome": "unavailable", "answer": None, "status": "ERROR"}

    dns = harness.build_scenarios()[0]
    record = harness.run_scenario(dns, observe, 1)
    assert during == [("https://brane.invalid/api/v1", "synthetic-outage-test", "synthetic-outage-test")]
    assert transport.ASSIGNED_BASE == transport.base_url() == base
    assert transport.api_key() == os.environ["BRANE_TOKEN"] == "synthetic-control-credential"
    assert record["verdict"] == "FAIL" and record["egress_attempts"] == []


def test_egress_requires_the_scenario_port_and_host():
    endpoint = "http://127.0.0.1:3042/api/v1"
    assert harness.check_egress([("connect", "127.0.0.1", 3042)], endpoint)[0]
    assert not harness.check_egress([("connect", "127.0.0.1", 3043)], endpoint)[0]
    assert not harness.check_egress([("connect", "127.0.0.2", 3042)], endpoint)[0]


def test_healthy_control_requires_observed_network_activity(monkeypatch):
    monkeypatch.setenv("BRANE_BASE_URL", transport.ASSIGNED_BASE)
    healthy = harness.build_scenarios()[-1]
    record = harness.run_scenario(healthy, lambda *_args, **_kw: {
        "outcome": "direct", "status": "200", "answer": "Cached synthetic draft",
    }, 1)
    assert record["verdict"] == "FAIL" and record["egress_attempts"] == []
