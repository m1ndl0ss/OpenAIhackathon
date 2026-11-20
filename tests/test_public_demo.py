import secrets
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import brane_client, public_demo


@pytest.fixture
def demo_client(monkeypatch):
    monkeypatch.setenv("REDWOOD_DEMO_SIGNING_KEY", secrets.token_hex(32))
    monkeypatch.setenv("CLEARANCE_MODE", "live")
    monkeypatch.setattr(brane_client, "send_turn", lambda **kwargs: pytest.fail("Public demo called BRANE"))
    public_demo.signing_key.cache_clear()
    with TestClient(public_demo.app) as client:
        yield client
    public_demo.signing_key.cache_clear()


def test_visitor_can_open_desks_and_recover_the_same_sealed_case(demo_client):
    def visit(workspace, route, token=None, body=None):
        response = demo_client.post("/api/demo", json={
            "path": route, "workspace": workspace, "desk_token": token, "body": body,
            "action_key": uuid4().hex if body is not None else None,
        })
        assert response.status_code == 200
        return response.json()

    start = visit(None, "/entry")
    assert len(start["data"]["desks"]) == 6 and len(start["data"]["departments"]) == 26
    session = visit(start["workspace"], "/demo-session", body={"desk_id": "staff-coverage"})
    token, workspace = session["data"]["token"], session["workspace"]
    assert session["data"]["staff"]["configured_mode"] == "fixture"
    assert len(visit(workspace, "/request-types")["data"]) == 27
    route = "/cases/LC-001"
    run = visit(workspace, route + "/runs", token, {"revision": 1, "mode": "fixture"})
    assert run["status"] == 202
    saved = visit(run["workspace"], route, token)["data"]
    assert saved["last_run"]["status"] == "sealed" and saved["recommendation"]
    assert saved["configured_mode"] == saved["last_run"]["mode"] == "fixture"

    separate = visit(None, "/demo-session", body={"desk_id": "staff-coverage"})
    assert visit(separate["workspace"], route, token)["status"] == 401
    fresh = visit(separate["workspace"], route, separate["data"]["token"])["data"]
    assert fresh["last_run"] is None and fresh["packet_hash"] is None


def test_invalid_workspace_and_live_mode_are_rejected(demo_client):
    assert demo_client.post("/api/demo", json={"path": "/entry", "workspace": "not-a-workspace"}).status_code == 410
    assert demo_client.post("/api/demo", json={
        "path": "/cases/LC-001/runs", "body": {"mode": "live", "revision": 1},
    }).status_code == 422
