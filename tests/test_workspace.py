import csv
import os
import sys

import pytest

from backend import brane_client, demo
from backend.agent.packets import headroom_after
from backend.store import transaction


def test_repeatable_setup_and_named_demo_reset(tmp_path, monkeypatch):
    monkeypatch.setenv("CLEARANCE_HOME", str(tmp_path))
    monkeypatch.delenv("CLEARANCE_DB_PATH", raising=False)

    def run(command):
        monkeypatch.setattr(sys, "argv", ["backend.demo", command])
        demo.main()

    run("setup")
    path, first = demo.settings()
    assert len(first) == len({person["id"] for person in first.values()}) == 6 + 2 * 26
    if os.name == "posix":
        assert (tmp_path / "sessions.json").stat().st_mode & 0o077 == 0
    for policy in ("baseline", "hardened"):
        with (tmp_path / "evidence" / f"{policy}.csv").open(newline="") as source:
            rows = list(csv.DictReader(source))
        assert [r["Test ID"] for r in rows] == [f"{p}{i}" for p in ("T", "E") for i in range(1, 6)]
        assert {r["Pass/Fail"] for r in rows} == {"UNVERIFIED"}
    matrix = tmp_path / "evidence/policy-matrix.csv"
    matrix.write_text("Synthetic reviewed work in progress\n")
    with transaction(path, write=True) as db:
        db.execute("CREATE TABLE local_reset_marker(id INTEGER PRIMARY KEY)")
    run("setup")
    with transaction(path) as db:
        assert db.execute("SELECT count(*) FROM local_reset_marker").fetchone()[0] == 0
    run("reset")
    with transaction(path) as db:
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='local_reset_marker'").fetchone()
        case_ids = {r[0] for r in db.execute("SELECT id FROM cases")}
        assert {"LC-001", "LC-002"} <= case_ids
        assert len(case_ids) == 2 + 2 * 26
    assert demo.settings()[1] == first
    assert matrix.read_text() == "Synthetic reviewed work in progress\n"
    other = tmp_path / "other.sqlite3"
    monkeypatch.setenv("CLEARANCE_DB_PATH", str(other))
    with pytest.raises(RuntimeError, match="local demo.sqlite3"):
        run("reset")
    assert not other.exists()


def test_headroom_requires_usable_current_inputs():
    case = demo.demo_case()
    assert headroom_after(case) == 50_000_000
    assert headroom_after({**case, "amount_minor": 300_000_000}) == -50_000_000
    for bad in ({"limit_minor": None}, {"currency": "EUR"}, {"expiry": "2026-12-01"}):
        assert headroom_after({**case, "facility": {**case["facility"], **bad}}) is None
    assert headroom_after({**case, "expiry": "2026-01-31"}) is None


def test_brane_probe_requires_team_credential_and_https(monkeypatch):
    monkeypatch.delenv("BRANE_API_KEY", raising=False)
    monkeypatch.delenv("BRANE_TOKEN", raising=False)
    monkeypatch.setenv("BRANE_BASE_URL", "https://brane.ai-z.io/api/v1/")
    with pytest.raises(RuntimeError, match="credential"):
        brane_client.live_config()
    monkeypatch.setenv("BRANE_API_KEY", "synthetic-probe-key")
    assert brane_client.live_config()[0] == "https://brane.ai-z.io/api/v1"
    monkeypatch.setenv("BRANE_BASE_URL", "http://assigned.example/api/v1/")
    with pytest.raises(RuntimeError, match="HTTPS"):
        brane_client.live_config()


def test_one_click_desk_is_scoped_to_local_fixture(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import create_app

    monkeypatch.setenv("CLEARANCE_DEMO_LOGIN", "1")
    people = demo.make_principals()
    path = tmp_path / "demo.sqlite3"
    app = create_app(path, people, mode="fixture")
    local = {"base_url": "http://127.0.0.1:8000", "client": ("127.0.0.1", 43100)}
    prefix = "/v2/trade"
    with TestClient(app, **local) as client:
        desks = client.get(prefix + "/entry").json()["desks"]
        assert {desk["role"] for desk in desks} == set(demo.ROLES)
        assert all(set(d) == {"name", "id", "role"} for d in desks)
        body = {"desk_id": desks[0]["id"]}
        assert client.post(prefix + "/demo-session", json={"desk_id": "unassigned"}).status_code == 404
        for desk in desks:
            issued = client.post(prefix + "/demo-session", json={"desk_id": desk["id"]})
            assert issued.status_code == 200 and issued.headers["Cache-Control"] == "no-store"
            token = issued.json()["token"]
            assert token not in people
            headers = {"Authorization": "Bearer " + token}
            me = client.get(prefix + "/me", headers=headers).json()
            assert me["id"] == desk["id"] and me["desk_picker"]
            assert client.get(prefix + "/cases", headers=headers).status_code == 200
        for extra in ({"Origin": "https://external.example"}, {"Host": "external.example"},
                      {"Sec-Fetch-Site": "cross-site"}):
            assert client.post(prefix + "/demo-session", json=body, headers=extra).status_code == 404
    with TestClient(app, base_url=local["base_url"], client=("192.0.2.8", 43100)) as remote:
        assert remote.get(prefix + "/entry").json()["desks"] == []
        assert remote.get(prefix + "/me", headers=headers).status_code == 401
    with TestClient(create_app(path, people, mode="live"), **local) as live:
        assert live.get(prefix + "/entry").json()["desks"] == []
        assert live.post(prefix + "/demo-session", json=body).status_code == 404
        assert live.get(prefix + "/me", headers=headers).status_code == 401
        assert live.get(prefix + "/me", headers={"Authorization": "Bearer " + next(iter(people))}).is_success


def test_one_click_live_rehearsal_is_disposable_and_loopback_only(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.live_demo import rehearsal_app

    monkeypatch.setenv("BRANE_BASE_URL", brane_client.ASSIGNED_BASE)
    monkeypatch.setenv("BRANE_API_KEY", "fixture-credential")
    monkeypatch.setenv("BRANE_MODEL", "dummy")
    monkeypatch.setenv("BRANE_POLICY_VERSION", "hardened-v2")
    local = {"base_url": "http://127.0.0.1:8001", "client": ("127.0.0.1", 4400)}
    with rehearsal_app() as app:
        database = app.state.path
        with TestClient(app, **local) as client:
            entry = client.get("/v2/trade/entry").json()
            assert entry["mode"] == "live" and len(entry["desks"]) == 6
            desk = {"desk_id": entry["desks"][0]["id"]}
            reply = client.post("/v2/trade/demo-session", json=desk).json()
            assert reply["staff"]["configured_mode"] == "live" and reply["staff"]["analysis_available"]
            assert client.post("/v2/trade/demo-session", json=desk, headers={"Origin": "https://example.org"}).status_code == 404
    assert not database.exists()


@pytest.mark.parametrize("url", ["https://other.example/api/v1", "https://brane.ai-z.io:444/api/v1",
                                 "https://brane.ai-z.io/api/v1/other"])
def test_live_host_is_pinned(monkeypatch, url):
    monkeypatch.setenv("BRANE_BASE_URL", url)
    with pytest.raises(RuntimeError, match="assigned HTTPS"):
        brane_client.live_config()


def test_unreachable_firewall_observed_at_transport_boundary(tmp_path):
    import json
    import subprocess

    output = tmp_path / "outage.json"
    subprocess.run([sys.executable, "-m", "tools.firewall_outage", "--output", str(output)], check=True)
    report = json.loads(output.read_text())
    assert report["verdict"] == "PASS" and report["model_post_attempts"] == 0
    assert not report["sealed"] and not report["receipt"]
