"""Local workspace bootstrap. Run from the repository root with python -m backend.demo."""

import argparse
import csv
import json
import os
import secrets
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

from . import departments

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/trade/demo.json"
TEST_PROTOCOL = ROOT / "submission/MAIN_Five_Tests_Template.csv"
POLICY_MATRIX = ROOT / "submission/MAIN_Policy_Matrix_Template.csv"
ROLES = ("coverage", "trade_finance", "credit_risk", "compliance", "final_officer", "operations")


def demo_case():
    return json.loads(FIXTURE.read_text())["case"]


def make_principals(*, specialists=False):
    fixture = json.loads(FIXTURE.read_text())
    return {
        secrets.token_urlsafe(32): {**staff, "customer_ref": fixture["case"]["customer_ref"]}
        for staff in (departments.staff_directory() if specialists else fixture["staff"])
    }


def local_dir():
    return Path(os.getenv("CLEARANCE_HOME", ROOT / ".clearance")).expanduser().resolve()


def settings():
    directory = local_dir()
    session_file = directory / "sessions.json"
    if not session_file.is_file():
        raise RuntimeError("Local logins are missing. Run make setup first.")
    def unique_keys(pairs):
        values = dict(pairs)
        if len(pairs) != len(values):
            raise RuntimeError("Duplicate entry in local login configuration.")
        return values

    with session_file.open() as source:
        principals = json.load(source, object_pairs_hook=unique_keys)
    if not isinstance(principals, dict) or not all(isinstance(p, dict) for p in principals.values()):
        raise RuntimeError("Invalid local login configuration.")
    roles = {person.get("role") for person in principals.values()}
    ids = {person.get("id") for person in principals.values()}
    if (roles != set(ROLES) or len(principals) != len(ROLES) or len(ids) != len(ROLES)
            or None in ids or any(len(token) < 32 for token in principals)):
        raise RuntimeError("Local login configuration is incomplete.")
    additional = directory / "department-sessions.json"
    if additional.exists():
        specialists = json.loads(additional.read_text(), object_pairs_hook=unique_keys)
        expected = {p["role"] for p in departments.staff_directory()}
        if (not isinstance(specialists, dict) or not all(isinstance(p, dict) for p in specialists.values())
                or {p.get("role") for p in specialists.values()} != expected or len(specialists) != len(expected)
                or any(not isinstance(t, str) or len(t) < 32 or t in principals for t in specialists)):
            raise RuntimeError("Department login configuration is incomplete.")
        principals.update(specialists)
    return Path(os.getenv("CLEARANCE_DB_PATH", directory / "demo.sqlite3")).expanduser().resolve(), principals


def create_sessions(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_sessions(directory / "sessions.json", specialists=False)
    write_sessions(directory / "department-sessions.json", specialists=True)


def write_sessions(destination, *, specialists):
    if destination.exists():
        return
    # Publish the completed file atomically. Windows must close the draft before
    # creating its final name or removing the draft link.
    draft = tempfile.NamedTemporaryFile(mode="w", dir=destination.parent, delete=False)
    try:
        with draft:
            json.dump(make_principals(specialists=specialists), draft, indent=2)
            draft.flush()
            os.fsync(draft.fileno())
        try:
            os.link(draft.name, destination)
        except FileExistsError:
            pass
    finally:
        Path(draft.name).unlink(missing_ok=True)


EDGE_CASES = {
    "E1": ("Case and desk isolation", "Only assigned staff can see their case and permitted evidence"),
    "E2": ("Local and cloud boundary", "Restricted evidence stays local or is refused; shared facts remain useful"),
    "E3": ("Open Compliance hold", "Approval and issuance stay blocked until the owning desk clears the hold"),
    "E4": ("Stale review and concurrent retries", "Current review produces one decision and one durable simulated receipt"),
    "E5": ("Firewall unavailable", "Model work stops without a new sealed packet or a cloud fallback"),
}


def prepare_evidence(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with TEST_PROTOCOL.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        scenarios = []
        for row in reader:
            test_id = row["Test ID"]
            name, expected = EDGE_CASES.get(test_id, (row["Scenario type"], row["Expected result"]))
            scenarios.append({"Test ID": test_id, "Scenario type": name, "Expected result": expected})
    for version in ("baseline", "hardened"):
        output = directory / f"{version}.csv"
        try:
            target = output.open("x", encoding="utf-8", newline="")
        except FileExistsError:
            continue
        with target:
            writer = csv.DictWriter(target, fieldnames=fields)
            writer.writeheader()
            for scenario in scenarios:
                writer.writerow({**scenario, "Pass/Fail": "UNVERIFIED", "Team / Policy version": version})
    matrix = directory / "policy-matrix.csv"
    if not matrix.exists():
        with POLICY_MATRIX.open(encoding="utf-8", newline="") as source:
            header = next(csv.reader(source))
        with matrix.open("x", encoding="utf-8", newline="") as dest:
            csv.writer(dest).writerow(header)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("setup", "reset", "doctor"):
        cmd = commands.add_parser(name)
        if name == "doctor":
            cmd.add_argument("--brane", action="store_true", help="Check the team's live policy endpoint")
    commands.add_parser("logins")
    commands.add_parser("login").add_argument("role", choices=(*ROLES, *(person["role"] for person in departments.staff_directory())))
    args = parser.parse_args()
    directory = local_dir()
    if args.command == "setup":
        create_sessions(directory)
    db_path, principals = settings()
    if args.command in {"setup", "reset"}:
        from backend.store import initialize

        if args.command == "reset":
            if db_path != directory / "demo.sqlite3":
                raise RuntimeError("Reset only supports the local demo.sqlite3. Custom database paths are preserved.")
            with tempfile.TemporaryDirectory(dir=directory) as scratch:
                fresh = Path(scratch) / "demo.sqlite3"
                initialize(fresh, principals)
                with closing(sqlite3.connect(fresh)) as source, closing(sqlite3.connect(db_path)) as destination:
                    source.backup(destination)
        else:
            initialize(db_path, principals)
        prepare_evidence(directory / "evidence")
        print(f"Demo database: {db_path}\nEvidence workbooks: {directory / 'evidence'}")
    elif args.command == "logins":
        for person in principals.values():
            print(f"{person['role']:16} {person['name']}")
    elif args.command == "login":
        print(next(token for token, person in principals.items() if person["role"] == args.role))
    elif args.command == "doctor":
        from backend.brane_client import check_policy

        mode = os.environ.get("CLEARANCE_MODE", "fixture")
        if mode not in {"live", "fixture"}:
            raise RuntimeError("CLEARANCE_MODE must be fixture or live.")
        if not db_path.is_file():
            raise RuntimeError("Demo database is missing. Run make setup.")
        print(f"Database ready · {len(principals)} human logins · {mode} mode")
        console = ROOT / "console/dist/index.html"
        if not console.is_file():
            raise RuntimeError("Console build is missing. Run make build.")
        print("Console build ready.")
        if args.brane:
            from scripts.brane_client import load_env
            load_env()
            print(f"BRANE policy matches the committed rules · {check_policy()}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, sqlite3.Error) as error:
        sys.exit(str(error))
