"""Human workflow regressions. Each test gets its own synthetic SQLite database."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.demo import make_principals
from backend.main import create_app


CASES = "/v2/trade/cases"
STAGE = f"{CASES}/LC-001"
COMPLETE = f"{CASES}/LC-002"
DESKS = ("trade_finance", "credit_risk", "compliance")
CONFIDENTIAL_REASON = "Independent synthetic screening note retained by Compliance."


@pytest.fixture
def bank(tmp_path, monkeypatch):
    monkeypatch.setenv("CLEARANCE_MODE", "fixture")
    principals = make_principals()
    tokens = {person["role"]: token for token, person in principals.items()
              if person["customer_ref"] == "ORG_DEMO_01"}
    path = tmp_path / "workflow.sqlite3"
    with TestClient(create_app(path, principals)) as client:
        yield client, tokens, path, principals


def headers(tokens, role, key=None):
    result = {"Authorization": f"Bearer {tokens[role]}"}
    if key is not None:
        result["Idempotency-Key"] = key
    return result


def post(bank, path, role, body, key=None):
    client, tokens, *_ = bank
    return client.post(path, json=body, headers=headers(tokens, role, key or str(uuid4())))


def read(bank, path, role="coverage"):
    client, tokens, *_ = bank
    response = client.get(path, headers=headers(tokens, role))
    assert response.status_code == 200, response.text
    return response.json()


def ok(response):
    assert response.is_success, response.text
    return response.json()


def seal(bank, path):
    revision = read(bank, path)["revision"]
    run = post(bank, path + "/runs", "coverage", {"revision": revision, "mode": "fixture"})
    assert run.status_code == 202, run.text
    run_id = run.json()["run_id"]
    read(bank, path + f"/runs/{run_id}")
    detail = read(bank, path)
    assert len(detail["packet_hash"]) == 64
    return detail, run_id


def binding(case):
    return {"revision": case["revision"], "packet_hash": case["packet_hash"]}


def review(bank, path, case, desk, disposition="clear", **changes):
    body = {
        **binding(case),
        "disposition": disposition,
        "reason_code": "CHECKS_COMPLETE" if disposition == "clear" else "MANUAL_REVIEW",
        "reason": f"The {desk} reviewer examined the current synthetic file.",
        "expected_review_event_id": None,
        **changes,
    }
    return post(bank, f"{path}/reviews/{desk}", desk, body)


def decision(case):
    return {**binding(case), "decision": "approve",
            "reason": "The three desk reviews support this instrument within my mandate."}


def concurrent_posts(bank, path, role, body, keys):
    barrier = Barrier(len(keys))

    def submit(key):
        barrier.wait(timeout=10)
        return post(bank, path, role, body, key)

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        return list(pool.map(submit, keys))


def test_e3_independent_compliance_hold(bank, record_property):
    """The invoice is present and Trade and Credit have cleared; only Compliance can release its hold."""
    case, run_id = seal(bank, COMPLETE)
    assert case["invoice_ref"]
    for desk in ("trade_finance", "credit_risk"):
        ok(review(bank, COMPLETE, case, desk))
    ok(review(bank, COMPLETE, case, "compliance", "hold", reason=CONFIDENTIAL_REASON))

    owned = read(bank, COMPLETE, "compliance")
    held = read(bank, COMPLETE, "final_officer")
    assert held["status"] == "on_hold"
    assert [h["desk"] for h in held["holds"]] == ["compliance"]
    assert held["invoice_ref"] and held["decision"] is None and held["receipt"] is None
    assert {r["desk"] for r in held["reviews"] if r["disposition"] == "clear"} == {
        "trade_finance", "credit_risk"
    }
    # The human reason remains inspectable by its owner, including after another desk opens the case.
    assert CONFIDENTIAL_REASON in json.dumps(owned)
    for role in ("coverage", "trade_finance", "credit_risk", "final_officer", "operations"):
        assert CONFIDENTIAL_REASON not in json.dumps(read(bank, COMPLETE, role))
        assert CONFIDENTIAL_REASON not in json.dumps(read(bank, COMPLETE + "/audit", role))

    denied_decision = post(bank, COMPLETE + "/decision", "final_officer", decision(case))
    denied_receipt = post(bank, COMPLETE + "/issuance", "operations", binding(case))
    assert (denied_decision.status_code, denied_receipt.status_code) == (409, 409)
    assert read(bank, COMPLETE, "operations")["receipt"] is None
    hold = held["holds"][0]["hold_id"]
    current = {r["desk"]: r["event_id"] for r in owned["reviews"]}
    resolution = {"resolves_hold_ids": [hold], "evidence_ref": "SCREEN-01@1"}
    wrong_desk = review(bank, COMPLETE, case, "credit_risk",
                        expected_review_event_id=current["credit_risk"], **resolution)
    assert wrong_desk.status_code in (403, 409, 422)
    assert read(bank, COMPLETE)["status"] == "on_hold"
    ok(review(bank, COMPLETE, case, "compliance",
              expected_review_event_id=current["compliance"], **resolution))
    assert read(bank, COMPLETE)["status"] == "ready_for_decision"
    ok(post(bank, COMPLETE + "/decision", "final_officer", decision(case)))
    assert read(bank, COMPLETE, "operations")["receipt"] is None
    record_property("observed",
                    f"fixture LC-002 rev {case['revision']}, run {run_id}, sealed {case['packet_hash']}; "
                    f"invoice present, Trade and Credit cleared, Compliance held. Decision "
                    f"HTTP {denied_decision.status_code} ({denied_decision.json()['code']}), issuance "
                    f"HTTP {denied_receipt.status_code} ({denied_receipt.json()['code']}), 0 receipts. "
                    f"Credit release HTTP {wrong_desk.status_code}; Compliance release made file ready; "
                    "final officer approved, 0 receipts before Operations.")


def test_e4_revision_retries_and_restart(bank, record_property):
    """A fresh invoice invalidates the old packet. Concurrent retries produce one durable receipt."""
    original, first_run = seal(bank, STAGE)
    ok(review(bank, STAGE, original, "credit_risk"))
    missing = review(bank, STAGE, original, "trade_finance")
    assert missing.status_code == 409
    ok(review(bank, STAGE, original, "compliance", "hold", reason_code="DOCUMENT_REQUIRED",
              request_to="coverage", required_evidence="supplier_invoice"))
    pending = read(bank, STAGE, "coverage")
    invoice_request = pending["requests"][0]["request_id"]
    ok(post(bank, STAGE + "/evidence", "coverage", {
        "expected_revision": original["revision"], "fixture_document_id": "DOC-INV-01",
        "request_id": invoice_request, "note": "Supplier invoice supplied for this case."
    }))
    amended = read(bank, STAGE)
    assert amended["status"] == "on_hold" and amended["packet_hash"] is None
    assert amended["revision"] == original["revision"] + 1
    hold_id = amended["holds"][0]["hold_id"]
    current, current_run = seal(bank, STAGE)
    assert current["packet_hash"] != original["packet_hash"]
    assert not any(item["disposition"] == "clear" for item in current["reviews"])
    ok(review(bank, STAGE, current, "trade_finance"))
    ok(review(bank, STAGE, current, "credit_risk"))
    ok(review(bank, STAGE, current, "compliance", resolves_hold_ids=[hold_id],
              evidence_ref="DOC-INV-01@1"))
    assert read(bank, STAGE)["status"] == "ready_for_decision"
    stale = post(bank, STAGE + "/decision", "final_officer", decision(original))
    assert stale.status_code == 409 and read(bank, STAGE)["decision"] is None
    approved = concurrent_posts(bank, STAGE + "/decision", "final_officer",
                                decision(current), [uuid4().hex, uuid4().hex])
    assert any(response.is_success for response in approved)
    assert all(response.is_success or response.status_code == 409 for response in approved)
    after_decision = read(bank, STAGE, "operations")
    assert after_decision["status"] == "approved" and after_decision["receipt"] is None
    key = uuid4().hex
    issued = concurrent_posts(bank, STAGE + "/issuance", "operations", binding(current), [key, key])
    receipts = [ok(response)["receipt_id"] for response in issued]
    assert len(set(receipts)) == 1 and receipts[0].startswith("SIM-")

    # A new application instance has no access to the first instance's in-memory state.
    _, tokens, path, principals = bank
    with TestClient(create_app(path, principals)) as reopened:
        fresh = reopened, tokens, path, principals
        existing = read(fresh, STAGE, "operations")
        assert existing["status"] == "issued_simulated"
        assert existing["receipt"]["receipt_id"] == receipts[0]
        for retry_key in (key, uuid4().hex):
            retry = post(fresh, STAGE + "/issuance", "operations", binding(current), retry_key)
            assert ok(retry)["receipt_id"] == receipts[0]
        audit = read(fresh, STAGE + "/audit", "operations")
    actions = [entry["action"] for entry in audit]
    assert actions.count("decision.approve") == 1
    assert actions.count("receipt.issued") == 1
    record_property("observed",
                    f"fixture LC-001 rev {original['revision']} -> {current['revision']}, "
                    f"runs {first_run}, {current_run}, sealed {current['packet_hash']}; "
                    f"stale decision HTTP {stale.status_code} ({stale.json()['code']}); "
                    f"concurrent decision HTTP {[r.status_code for r in approved]}, "
                    f"concurrent issuance HTTP {[r.status_code for r in issued]}; after reopen "
                    f"{actions.count('decision.approve')} approval event and "
                    f"{actions.count('receipt.issued')} issuance event, persisted receipt {receipts[0]}.")


def test_authentication_assignments_and_roles(bank):
    client, tokens, path, principals = bank
    assert client.get(CASES).status_code == 401
    assert client.get(CASES, headers={"Authorization": "Bearer invalid"}).status_code == 401
    for desk, token in tokens.items():
        profile = read(bank, "/v2/trade/me", desk)
        assert profile["role"] == desk and profile["id"] == principals[token]["id"]

    # A separately enrolled group owns another customer; it must never see LC-001.
    foreign_principals = dict(principals)
    for token, person in principals.items():
        foreign_principals[f"other-{token}"] = {
            **person, "id": f"other-{person['id']}", "customer_ref": "ORG_DEMO_03",
        }
    with TestClient(create_app(path.parent / "isolation.sqlite3", foreign_principals)) as other:
        foreign = {"Authorization": f"Bearer other-{tokens['coverage']}"}
        assert all(row["case_id"] != "LC-001" for row in other.get(CASES, headers=foreign).json())
        for suffix in ("", "/audit"):
            hidden = other.get(STAGE + suffix, headers=foreign)
            unknown = other.get(CASES + "/LC-ABSENT" + suffix, headers=foreign)
            assert hidden.status_code == unknown.status_code == 404
            assert hidden.json()["code"] == unknown.json()["code"]

    case, _ = seal(bank, COMPLETE)
    wrong_final = post(bank, COMPLETE + "/decision", "coverage", decision(case))
    wrong_ops = post(bank, COMPLETE + "/issuance", "final_officer", binding(case))
    assert wrong_final.status_code == wrong_ops.status_code == 403
    assert read(bank, COMPLETE)["decision"] is None


def test_review_precondition_and_idempotency_body_conflict(bank):
    case, _ = seal(bank, COMPLETE)
    url = COMPLETE + "/reviews/credit_risk"
    payload = {**binding(case), "disposition": "clear", "reason_code": "CHECKS_COMPLETE",
               "reason": "Capacity and the facility expiry were checked.", "expected_review_event_id": None}
    key = uuid4().hex
    initial = post(bank, url, "credit_risk", payload, key)
    assert initial.is_success
    replay = post(bank, url, "credit_risk", payload, key)
    assert replay.status_code == initial.status_code and replay.json() == initial.json()
    modified = {**payload, "reason": "A newer finding would need its predecessor reference."}
    assert post(bank, url, "credit_risk", modified, key).status_code == 409
    assert post(bank, url, "credit_risk", modified).status_code == 409
    assert [r["action"] for r in read(bank, COMPLETE + "/audit")].count("review.clear") == 1


def test_existing_packet_cannot_be_replaced(bank):
    first, run_id = seal(bank, STAGE)
    assert read(bank, STAGE + f"/runs/{run_id}")["status"]
    duplicate = post(bank, STAGE + "/runs", "coverage", {"revision": first["revision"], "mode": "fixture"})
    assert duplicate.status_code == 409
    current = read(bank, STAGE)
    assert current["packet_hash"] == first["packet_hash"] and current["revision"] == first["revision"]


def test_digest_uses_normalized_canonical_json():
    from backend.store import canonical, digest

    assert digest({"revision": 1, "case_id": "LC-001"}) == (
        "af27b69a5a574b900145f146e581938600a6e40804b9f62f5a5f27184a053078"
    )
    assert canonical({"note": "cafe\u0301"}) == canonical({"note": "café"})
    with pytest.raises(ValueError):
        canonical({"é": "first", "e\u0301": "second"})
    with pytest.raises(ValueError):
        canonical({"amount_minor": 100.5})


def test_request_reply_is_scoped_and_does_not_change_the_sealed_file(bank):
    case, _ = seal(bank, COMPLETE)
    question = {"revision": case["revision"], "to_desk": "coverage",
                "question": "Can Coverage confirm the current terms match the intake?"}
    opened = ok(post(bank, COMPLETE + "/requests", "trade_finance", question))
    request_id = opened["request_id"]
    dest = COMPLETE + f"/requests/{request_id}/replies"
    reply = {"revision": case["revision"], "reply": "Coverage checked the intake and confirmed the terms."}
    assert post(bank, dest, "credit_risk", reply).status_code == 404
    assert not read(bank, COMPLETE, "credit_risk")["requests"]
    ok(post(bank, dest, "coverage", reply))
    updated = read(bank, COMPLETE, "trade_finance")
    assert binding(updated) == binding(case)
    entry, = updated["requests"]
    assert (entry["request_id"], entry["reply"], entry["status"]) == (
        request_id, reply["reply"], "answered"
    )


@pytest.mark.parametrize("fixture, amount", [
    ("LC-INSUFFICIENT", 300_000_000), ("LC-OVER-MANDATE", 200_000_000)
])
def test_bank_enforces_credit_and_officer_limits(bank, fixture, amount):
    case = ok(post(bank, CASES, "coverage", {
        "fixture_id": fixture, "customer_ref": "ORG_DEMO_01", "facility_ref": "FAC-USD-01",
        "amount_minor": amount, "currency": "USD", "instrument": "import_documentary_credit",
        "expiry": "2027-01-31"
    }))
    path = f"{CASES}/{case['case_id']}"
    case, _ = seal(bank, path)
    credit = review(bank, path, case, "credit_risk")
    if fixture == "LC-INSUFFICIENT":
        assert credit.status_code == 409 and credit.json()["code"] == "evidence_incomplete"
        assert read(bank, path)["status"] == "in_review"
    else:
        ok(credit)
        for desk in ("trade_finance", "compliance"):
            ok(review(bank, path, case, desk))
        assert read(bank, path)["status"] == "ready_for_decision"
        refusal = post(bank, path + "/decision", "final_officer", decision(case))
        assert refusal.status_code == 409 and refusal.json()["code"] == "mandate_exceeded"
        ok(post(bank, path + "/decision", "final_officer", {
            **binding(case), "decision": "refer", "reason": "Escalating to the higher credit authority."
        }))
        assert read(bank, path)["status"] == "referred"
    assert post(bank, path + "/issuance", "operations", binding(case)).status_code == 409


def test_unavailable_analysis_never_seals_the_file(bank, monkeypatch):
    from backend import integrations

    def unavailable_provider(snapshot, mode, **run):
        raise RuntimeError("Synthetic upstream detail for this test; keep it internal.")

    monkeypatch.setattr(integrations, "prepare_packets", unavailable_provider)
    _, tokens, path, principals = bank
    with TestClient(create_app(path, principals, mode="live")) as live:
        deployment = live, tokens, path, principals
        downgraded = post(deployment, STAGE + "/runs", "coverage", {"revision": 1, "mode": "fixture"})
        assert downgraded.status_code == 409 and downgraded.json()["code"] == "mode_mismatch"
        run = ok(post(deployment, STAGE + "/runs", "coverage", {"revision": 1, "mode": "live"}))
        result = read(deployment, STAGE + f"/runs/{run['run_id']}")
        assert result["status"] == "analysis_unavailable"
        case = read(deployment, STAGE)
        assert case["packet_hash"] is None and case["status"] == "preparing"
        assert "Synthetic upstream detail" not in json.dumps(read(deployment, STAGE + "/audit"))


def test_live_adapter_contract_can_seal_both_revisions(bank, monkeypatch):
    from backend import brane_client
    from backend.agent.runtime import ModelTurn

    monkeypatch.setattr(brane_client, "live_run_config", lambda: ("", "", "hardened-test", "test-model"))

    def governed_reply(**request):
        packet = json.loads(request["messages"][1]["content"])["approved_packets"][1]
        return ModelTurn("local", json.dumps(packet), {"provider_request_id": "synthetic-trace"})

    monkeypatch.setattr(brane_client, "send_turn", governed_reply)
    _, tokens, path, principals = bank
    with TestClient(create_app(path, principals, mode="live")) as client:
        live = client, tokens, path, principals
        for revision in (1, 2):
            submitted = ok(post(live, STAGE + "/runs", "coverage", {"revision": revision, "mode": "live"}))
            run = read(live, STAGE + f"/runs/{submitted['run_id']}")
            assert run["status"] == "sealed" and run["analysis"]["policy_version"] == "hardened-test"
            assert [item["task"] for item in run["analysis"]["observations"]] == ["draft_trade_finance"]
            trade = read(live, STAGE, "trade_finance")
            assert trade["mode"] == "live" and trade["revision"] == revision
            packet, = trade["packets"]
            assert packet["missing_items"] == (["supplier_invoice"] if revision == 1 else [])
            assert ("DOC-INV-01@1" in packet["evidence_refs"]) == (revision == 2)
            if revision == 1:
                ok(post(live, STAGE + "/evidence", "coverage", {
                    "fixture_document_id": "DOC-INV-01", "expected_revision": revision,
                }))


@pytest.mark.parametrize("already_issued", [False, True], ids=["approved", "existing-receipt"])
def test_live_deployment_refuses_fixture_approval_and_issuance_replays(bank, already_issued):
    case, _ = seal(bank, COMPLETE)
    for desk in DESKS:
        ok(review(bank, COMPLETE, case, desk))
    approval_key, receipt_key = uuid4().hex, uuid4().hex
    ok(post(bank, COMPLETE + "/decision", "final_officer", decision(case), approval_key))
    receipt_id = None
    if already_issued:
        receipt_id = ok(post(bank, COMPLETE + "/issuance", "operations", binding(case), receipt_key))["receipt_id"]
    _, tokens, path, principals = bank
    with TestClient(create_app(path, principals, mode="live")) as live:
        deployment = live, tokens, path, principals
        assert read(deployment, "/v2/trade/me", "operations")["configured_mode"] == "live"
        ops = read(deployment, COMPLETE, "operations")
        assert "issue" not in ops["permitted_actions"]
        assert ops["status"] == ("issued_simulated" if already_issued else "approved")
        assert (ops["receipt"]["receipt_id"] if already_issued else ops["receipt"]) == receipt_id
        for request in (
            post(deployment, COMPLETE + "/decision", "final_officer", decision(case), approval_key),
            post(deployment, COMPLETE + "/issuance", "operations", binding(case), receipt_key),
            post(deployment, COMPLETE + "/issuance", "operations", binding(case)),
        ):
            assert request.status_code == 409 and request.json()["code"] == "mode_mismatch"
        actions = [row["action"] for row in read(deployment, COMPLETE + "/audit", "operations")]
        assert actions.count("decision.approve") == 1
        assert actions.count("receipt.issued") == int(already_issued)


def test_overlapping_analysis_can_only_seal_once(bank, monkeypatch):
    from backend import integrations

    overlap = Barrier(2)
    prepare = integrations.prepare_packets

    def prepare_together(snapshot, mode, **run):
        overlap.wait(timeout=10)
        return prepare(snapshot, mode, **run)

    monkeypatch.setattr(integrations, "prepare_packets", prepare_together)
    runs = concurrent_posts(bank, STAGE + "/runs", "coverage", {"mode": "fixture", "revision": 1},
                            [uuid4().hex, uuid4().hex])
    ids = [ok(response)["run_id"] for response in runs]
    states = sorted(read(bank, STAGE + f"/runs/{run_id}")["status"] for run_id in ids)
    assert states == ["sealed", "superseded"]
    assert read(bank, STAGE)["packet_hash"]


def test_amendment_during_analysis_discards_old_completion(bank, monkeypatch):
    from backend import integrations

    started, finish = Event(), Event()
    prepare = integrations.prepare_packets

    def delayed(snapshot, mode, **run):
        started.set()
        if not finish.wait(timeout=10):
            raise TimeoutError("The synthetic run was not released")
        return prepare(snapshot, mode, **run)

    monkeypatch.setattr(integrations, "prepare_packets", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(post, bank, STAGE + "/runs", "coverage", {"revision": 1, "mode": "fixture"})
        try:
            assert started.wait(timeout=10)
            ok(post(bank, STAGE + "/evidence", "coverage", {
                "fixture_document_id": "DOC-INV-01", "expected_revision": 1
            }))
        finally:
            finish.set()
        run_id = ok(pending.result())["run_id"]
    assert read(bank, STAGE + f"/runs/{run_id}")["status"] == "superseded"
    updated = read(bank, STAGE)
    assert updated["revision"] == 2 and updated["packet_hash"] is None
