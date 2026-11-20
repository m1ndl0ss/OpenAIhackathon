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
    assert len(first) == len({person["id"] for person in first.values()}) == 6
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
        assert [r[0] for r in db.execute("SELECT id FROM cases ORDER BY id")] == ["LC-001", "LC-002"]
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
    monkeypatch.setenv("BRANE_BASE_URL", "https://assigned.example/api/v1/")
    with pytest.raises(RuntimeError, match="credential"):
        brane_client.live_config()
    monkeypatch.setenv("BRANE_API_KEY", "synthetic-probe-key")
    assert brane_client.live_config()[0] == "https://assigned.example/api/v1"
    monkeypatch.setenv("BRANE_BASE_URL", "http://assigned.example/api/v1/")
    with pytest.raises(RuntimeError, match="HTTPS"):
        brane_client.live_config()
