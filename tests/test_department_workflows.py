"""Exercise each registered department through the staff API and shared drafting boundary."""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import brane_client, departments as dep, integrations
from backend.agent.runtime import ModelTurn, draft_messages, permitted_turn
from backend.demo import make_principals
from backend.main import create_app
from backend.store import canonical, initialize, transaction

BASE = "/v2/trade"
PROFILES = pytest.mark.parametrize("p", dep.CATALOG, ids=[p["code"] for p in dep.CATALOG])


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    people = {**make_principals(), **make_principals(specialists=True)}
    path = tmp_path_factory.mktemp("departments") / "cases.sqlite"
    client = TestClient(create_app(path, people, mode="fixture"))
    with client:
        yield client, {v["role"]: k for k, v in people.items()}, path, people


def get(workspace, path, role):
    client, keys, *_ = workspace
    return client.get(BASE + path, headers={"Authorization": "Bearer " + keys[role]})


def post(workspace, path, role, body, key=None):
    client, keys, *_ = workspace
    return client.post(BASE + path, headers={"Authorization": "Bearer " + keys[role],
                                            "Idempotency-Key": key or str(uuid4())}, json=body)


def checked(reply):
    assert reply.is_success, reply.text
    return reply.json()


@PROFILES
def test_seed_review_hold_revision_and_outcome(workspace, p):
    owner, head = dep.analyst(p), dep.approver(p)
    root = "/cases/" + p["code"] + "-002"
    queue = checked(get(workspace, "/cases", owner))
    assert {item["case_id"] for item in queue} == {p["code"] + "-001", p["code"] + "-002"}
    assert len({item["case_title"] for item in queue}) == 2
    outsider = next(role for role in ("operations", "trade_finance", "coverage") if role != p["partner"])
    assert get(workspace, root, outsider).status_code == 404
    assert get(workspace, "/cases/LC-001", owner).status_code == 404
    legacy = checked(get(workspace, "/cases/LC-001", "coverage"))
    assert legacy["workflow_id"] == dep.TRADE
    checked(post(workspace, root + "/runs", owner, {"revision": 1, "mode": "fixture"}))
    first = checked(get(workspace, root, owner))
    assert first["last_run"]["status"] == "sealed"
    assert [packet["desk"] for packet in first["packets"]] == list(dep.LANES)
    assert first["last_run"]["analysis"]["model_calls"] == (0 if p["local_only"] else 3)
    assert "sign" not in first["permitted_actions"] and "verify" in first["permitted_actions"]
    act = root + "/workflow-action"
    body = {"revision": 1, "packet_hash": first["packet_hash"], "reason": "Reviewed the registered synthetic evidence."}
    assert post(workspace, act, owner, {**body, "action": "complete"}).status_code == 403
    assert post(workspace, act, head, {**body, "action": "complete"}).status_code == 409
    checked(post(workspace, act, owner, {**body, "action": "hold"}))
    checked(post(workspace, act, owner, {"revision": 1, "action": "verify"}))
    assert post(workspace, act, owner, {**body, "action": "sign"}).status_code == 409
    checked(post(workspace, root + "/runs", owner, {"revision": 2, "mode": "fixture"}))
    revised = checked(get(workspace, root, owner))
    assert revised["holds"] and revised["status"] == "on_hold"
    assert revised["packet_hash"] != first["packet_hash"]
    assert {src["label"] for src in revised["sources"]} >= {p["source"]}
    assert any(src["detail"] == p["observations"][1] for src in revised["sources"])
    body.update(revision=2, packet_hash=revised["packet_hash"])
    for reviewer in dep.reviewers(p):
        if reviewer != owner:
            peer_view = checked(get(workspace, root, reviewer))
            assert p["observations"][1] not in json.dumps(peer_view, ensure_ascii=False)
            assert not any(ref.endswith("-SOURCE@1") for pack in peer_view["packets"] for ref in pack["evidence_refs"])
        checked(post(workspace, act, reviewer, {**body, "action": "sign"}))
    assert checked(get(workspace, root, head))["status"] == "ready_for_decision"
    key = str(uuid4())
    final = checked(post(workspace, act, head, {**body, "action": "complete"}, key))
    assert checked(post(workspace, act, head, {**body, "action": "complete"}, key)) == final
    # Open a fresh process against the same database and return the same outcome.
    _, keys, path, people = workspace
    with TestClient(create_app(path, people, mode="fixture")) as fresh:
        restored = checked(get((fresh, keys), root, head))
    assert restored["status"] == "completed" and restored["receipt"]["receipt_id"] == final["receipt_id"]
    assert restored["decision"]["actor_id"] == "staff-" + head
    assert restored["decision"]["actor_id"] not in {r["actor_id"] for r in restored["reviews"]}
    assert [e["action"] for e in checked(get(workspace, root + "/audit", owner))].count("decision.approve") == 1


@PROFILES
def test_complete_record_can_be_referred_and_cannot_be_reopened(workspace, p):
    root = "/cases/" + p["code"] + "-001"
    owner, head = dep.analyst(p), dep.approver(p)
    checked(post(workspace, root + "/runs", owner, {"revision": 1, "mode": "fixture"}))
    file = checked(get(workspace, root, owner))
    assert any(src["detail"] == p["observations"][0] for src in file["sources"])
    assert "verify" not in file["permitted_actions"]
    act = root + "/workflow-action"
    body = {"revision": 1, "packet_hash": file["packet_hash"], "reason": "Reviewed the synthetic record for internal referral."}
    for reviewer in dep.reviewers(p):
        assert post(workspace, act, head, {**body, "action": "refer"}).status_code == 409
        checked(post(workspace, act, reviewer, {**body, "action": "sign"}))
    outcome = checked(post(workspace, act, head, {**body, "action": "refer"}))
    restored = checked(get(workspace, root, head))
    assert restored["status"] == "referred" and restored["permitted_actions"] == []
    assert restored["receipt"]["receipt_id"] == outcome["receipt_id"]
    assert post(workspace, act, head, {**body, "action": "complete"}).status_code == 409


@PROFILES
@pytest.mark.parametrize("example", (1, 2))
def test_each_prompt_is_closed_and_every_private_marker_stays_local(p, example, monkeypatch):
    calls = []
    snapshot = dep.new_snapshot(p, "PRIVATE-CASE-MARKER", "PRIVATE-CUSTOMER-MARKER", example)
    snapshot["case_title"] = "PRIVATE-NOTE-MARKER repeated PRIVATE-NOTE-MARKER"
    monkeypatch.setattr(brane_client, "live_run_config", lambda: ("unused", "unused", "checked-test-policy", "test"))
    def model(**request):
        calls.append(request)
        assert permitted_turn(request["task"], request["messages"])
        projection = json.dumps(request["messages"])
        assert "PRIVATE-" not in projection
        assert all(obs not in projection for obs in p["observations"])
        assert not permitted_turn(request["task"], [*request["messages"], {"role": "user", "content": "unapproved input"}])
        wording = json.loads(request["messages"][-1]["content"])["wordings"][0]
        return ModelTurn("direct", json.dumps({"summary": wording}))
    monkeypatch.setattr(brane_client, "send_turn", model)
    result = integrations.prepare_packets(snapshot, "live", run_id="TEST", authorize=lambda: None)
    assert result.status == "prepared"
    assert len(calls) == result.model_calls == (0 if p["local_only"] else 3)
    if p["local_only"]:
        for lane in dep.LANES:
            step = "review" if example == 1 else "verify"
            assert not permitted_turn(dep.task_id(p, lane), draft_messages(lane, step, p))
        assert all(item["route"] == "bank_local" for item in result.observations)
    else:
        assert {r["task"] for r in calls} == {dep.task_id(p,lane) for lane in dep.LANES}
        monkeypatch.setattr(brane_client, "send_turn", lambda **kw: ModelTurn("unavailable"))
        stopped = integrations.prepare_packets(snapshot, "live", run_id="DOWN", authorize=lambda: None)
        assert stopped.status == "analysis_unavailable" and stopped.packets is None


def test_directory_and_fresh_case(workspace, monkeypatch):
    _, keys, path, people = workspace
    monkeypatch.setenv("CLEARANCE_DEMO_LOGIN", "1")
    with TestClient(create_app(path, people, mode="fixture"), base_url="http://127.0.0.1",
                    client=("127.0.0.1", 40001)) as client:
        entry = checked(client.get(BASE + "/entry"))
        assert len(entry["desks"]) == 6 and len(entry["departments"]) == 26
        assert {d["group"] for d in entry["departments"]} == {
            "Corporate banking", "Markets and securities", "Risk and control", "Group functions"}
        for d in entry["departments"]:
            for seat in ("analyst", "approver"):
                session = checked(client.post(BASE + "/demo-session", json={"desk_id": d[seat]["id"]}))
                assert session["staff"]["id"] == d[seat]["id"] and session["staff"]["desk_picker"]
    p = dep.CURRENT["kyc"]
    path = "/workflows/kyc/cases"
    assert post(workspace,path,"coverage",{"example":1}).status_code == 403
    key = str(uuid4())
    created = checked(post(workspace,path,dep.analyst(p),{"example":2},key))
    assert created["case_title"] == p["examples"][1]
    assert checked(post(workspace,path,dep.analyst(p),{"example":2},key))["case_id"] == created["case_id"]
    assert get(workspace,"/cases/" + created["case_id"],"coverage").status_code == 404


def test_mode_is_checked_before_replaying_a_department_signature(workspace):
    _, keys, path, people = workspace
    owner = dep.analyst(dep.CURRENT["kyc"])
    created = checked(post(workspace, "/workflows/kyc/cases", owner, {"example": 1}))
    root = "/cases/" + created["case_id"]
    checked(post(workspace, root + "/runs", owner, {"revision": 1, "mode": "fixture"}))
    file = checked(get(workspace, root, owner))
    key = str(uuid4())
    body = {"revision": 1, "packet_hash": file["packet_hash"], "action": "sign",
            "reason": "Confirmed the synthetic evidence for this packet."}
    checked(post(workspace, root + "/workflow-action", owner, body, key))
    with TestClient(create_app(path, people, mode="live")) as live:
        denied = post((live, keys), root + "/workflow-action", owner, body, key)
    assert denied.status_code == 409 and denied.json()["code"] == "mode_mismatch"


def test_adding_departments_preserves_a_sealed_legacy_case(tmp_path):
    old = make_principals()
    keys = {p["role"]: t for t, p in old.items()}
    path = tmp_path / "existing.sqlite"
    initialize(path, old)
    with transaction(path, write=True) as db:
        row = db.execute("SELECT snapshot FROM revisions WHERE case_id='LC-001' AND revision=1").fetchone()
        legacy = json.loads(row["snapshot"])
        legacy.pop("workflow_id")
        legacy.pop("definition_version")
        db.execute("UPDATE revisions SET snapshot=? WHERE case_id='LC-001' AND revision=1", (canonical(legacy),))
    with TestClient(create_app(path, old, mode="fixture")) as before:
        checked(post((before, keys), "/cases/LC-001/runs", "coverage", {"revision": 1, "mode": "fixture"}))
        original = checked(get((before, keys), "/cases/LC-001", "coverage"))
    people = {**old, **make_principals(specialists=True)}
    with TestClient(create_app(path, people, mode="fixture")) as after:
        preserved = checked(get((after, keys), "/cases/LC-001", "coverage"))
        assert preserved == original and preserved["workflow_id"] == dep.TRADE
        assert len(checked(get((after, keys), "/cases", "operations"))) > 2
