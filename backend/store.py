"""SQLite transaction and immutable synthetic case records."""

import hashlib
import json
import sqlite3
import unicodedata
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import departments
from .agent.tools import POLICY_REFS
from .demo import demo_case

DESKS = ("trade_finance", "credit_risk", "compliance")
ROLES = ("coverage", *DESKS, "final_officer", "operations")
ALL_ROLES = (*ROLES, *(person["role"] for person in departments.staff_directory()))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def identifier(prefix):
    return prefix + "-" + uuid4().hex


def canonical(value):
    def normalize(item):
        if isinstance(item, str):
            return unicodedata.normalize("NFC", item)
        if item is None or isinstance(item, (int, bool)):
            return item
        if isinstance(item, list):
            return [normalize(part) for part in item]
        if isinstance(item, dict):
            result = {}
            for key, val in item.items():
                if not isinstance(key, str):
                    raise ValueError("Expected a string key")
                key = normalize(key)
                if key in result:
                    raise ValueError("Duplicate normalized key")
                result[key] = normalize(val)
            return result
        raise ValueError("Expected an integer or a JSON value without floats")

    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def snapshot(case_id, customer, complete=False, fixture_id="LC-DEMO-001"):
    base = demo_case()
    stage = customer == base["customer_ref"]
    suffix = "01" if stage else hashlib.sha256(customer.encode()).hexdigest()[:8]
    facility_ref = base["facility_ref"] if stage else "FAC-" + suffix
    facility = {**base["facility"], "revision": 1}
    if fixture_id == "LC-EXPIRED-FACILITY":
        facility["expiry"] = "2026-11-19"
    if fixture_id == "LC-INVALID-FACILITY":
        facility["limit_minor"] = None
    return {
        "case_id": case_id,
        "workflow_id": departments.TRADE,
        "definition_version": 1,
        "customer_ref": customer,
        "supplier_ref": base["supplier_ref"] if stage else "SUP-" + suffix,
        "revision": 1,
        "amount_minor": 300000000 if fixture_id == "LC-INSUFFICIENT" else base["amount_minor"],
        "currency": base["currency"],
        "expiry": base["expiry"],
        "instrument": "import_documentary_credit",
        "as_of": base["as_of"],
        "facility_ref": facility_ref,
        "facility": facility,
        "invoice_ref": "DOC-INV-" + suffix + "@1" if complete else None,
        "invoice_document_id": "DOC-INV-" + suffix,
        "screen_ref": "SCREEN-" + suffix + "@1",
        "evidence_refs": sorted(
            ["INTAKE-" + suffix + "@1", "TRADE-" + suffix + "@1", facility_ref + "@1"]
            + (["DOC-INV-" + suffix + "@1"] if complete else [])
        ),
        "policy_refs": {desk: [ref] for desk, ref in POLICY_REFS.items()},
        "desk_list": list(DESKS),
        "bank_policy_version": "bank-fixture-v1",
        "brane_policy_version": "fixture-v1",
        "mandate_version": "mandate-v1",
        "mandate_minor": 150000000 if fixture_id == "LC-OVER-MANDATE" else base["mandate_limit_minor"],
        "mandate_currency": base["mandate_currency"],
        "mandate_expiry": "2027-03-31",
    }


def grouped_assignments(principals):
    groups, ids = {}, set()
    for token, p in principals.items():
        if (
            not token
            or not token.isascii()
            or any(c.isspace() for c in token)
            or not all(
                isinstance(p.get(k), str) and p[k].strip() for k in ("id", "name", "role", "customer_ref")
            )
            or p["role"] not in ALL_ROLES
            or p["id"] in ids
        ):
            raise ValueError("Invalid or duplicate demo identity")
        group = groups.setdefault(p["customer_ref"], {})
        if p["role"] in group:
            raise ValueError("Duplicate desk assignment")
        ids.add(p["id"])
        group[p["role"]] = p["id"]
    if not groups or any(not set(ROLES).issubset(g) for g in groups.values()):
        raise ValueError("Each demo customer needs six distinct assigned people")
    return groups


SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY, customer TEXT NOT NULL, assignments TEXT NOT NULL, revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
    case_id TEXT NOT NULL REFERENCES cases(id), revision INTEGER NOT NULL, snapshot TEXT NOT NULL,
    packets TEXT, packet_hash TEXT, mode TEXT, sealed_at TEXT, run_id TEXT,
    PRIMARY KEY(case_id, revision)
);
CREATE TRIGGER IF NOT EXISTS sealed_revision BEFORE UPDATE ON revisions WHEN OLD.packet_hash IS NOT NULL
    BEGIN SELECT RAISE(ABORT, 'Sealed revision'); END;
CREATE TABLE IF NOT EXISTS audit (
    sequence INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, case_id TEXT NOT NULL REFERENCES cases(id),
    revision INTEGER NOT NULL, actor_id TEXT NOT NULL, desk TEXT NOT NULL, action TEXT NOT NULL,
    timestamp TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_case ON audit(case_id,sequence);
CREATE TRIGGER IF NOT EXISTS immutable_audit_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'Append only'); END;
CREATE TRIGGER IF NOT EXISTS immutable_audit_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'Append only'); END;
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), revision INTEGER NOT NULL,
    mode TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT
);
CREATE TABLE IF NOT EXISTS run_analysis (
    run_id TEXT PRIMARY KEY REFERENCES runs(run_id), details TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    event_id TEXT PRIMARY KEY REFERENCES audit(event_id), case_id TEXT NOT NULL, revision INTEGER NOT NULL,
    desk TEXT NOT NULL, disposition TEXT NOT NULL, actor_id TEXT NOT NULL, reason_code TEXT NOT NULL,
    reason TEXT NOT NULL, packet_hash TEXT NOT NULL, supersedes TEXT,
    FOREIGN KEY(case_id,revision) REFERENCES revisions(case_id,revision)
);
CREATE TABLE IF NOT EXISTS holds (
    hold_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), revision INTEGER NOT NULL,
    desk TEXT NOT NULL, reason_code TEXT NOT NULL, resolved_event TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_desk_hold ON holds(case_id,desk) WHERE resolved_event IS NULL;
CREATE TABLE IF NOT EXISTS hold_resolutions (
    hold_id TEXT PRIMARY KEY REFERENCES holds(hold_id), review_event TEXT NOT NULL REFERENCES reviews(event_id),
    evidence_ref TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), revision INTEGER NOT NULL,
    from_desk TEXT NOT NULL, to_desk TEXT NOT NULL, question TEXT NOT NULL, status TEXT NOT NULL,
    hold_id TEXT REFERENCES holds(hold_id), reply TEXT, evidence_ref TEXT, answered_revision INTEGER
);
CREATE TABLE IF NOT EXISTS decisions (
    case_id TEXT PRIMARY KEY REFERENCES cases(id), revision INTEGER NOT NULL, packet_hash TEXT NOT NULL,
    actor_id TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT NOT NULL, timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS receipts (
    case_id TEXT PRIMARY KEY REFERENCES decisions(case_id), receipt_id TEXT NOT NULL UNIQUE,
    revision INTEGER NOT NULL, packet_hash TEXT NOT NULL, actor_id TEXT NOT NULL, timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS retries (
    principal TEXT NOT NULL, operation TEXT NOT NULL, resource TEXT NOT NULL, key TEXT NOT NULL,
    body_hash TEXT NOT NULL, status INTEGER NOT NULL, response TEXT NOT NULL,
    PRIMARY KEY(principal,operation,resource,key)
);
"""


@contextmanager
def transaction(path, write=False):
    with closing(sqlite3.connect(path, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        with db:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db


def event(db, s, actor, action, detail):
    ref = identifier("EV")
    db.execute(
        "INSERT INTO audit(event_id,case_id,revision,actor_id,desk,action,timestamp,detail) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (ref, s["case_id"], s["revision"], actor["id"], actor["role"], action, now(), detail),
    )
    return ref


def insert_case(db, s, assignments, actor):
    db.execute(
        "INSERT INTO cases VALUES(?,?,?,?)",
        (s["case_id"], s["customer_ref"], canonical(assignments), s["revision"]),
    )
    db.execute(
        "INSERT INTO revisions(case_id,revision,snapshot) VALUES(?,?,?)",
        (s["case_id"], s["revision"], canonical(s)),
    )
    event(db, s, actor, "case.opened", "Synthetic intake opened.")


def initialize(path, principals):
    groups = grouped_assignments(principals)
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
    with transaction(path, write=True) as db:
        for customer, group in groups.items():
            stage = customer == "ORG_DEMO_01"
            suffix = hashlib.sha256(customer.encode()).hexdigest()[:8]
            seeds = [("LC-001", False), ("LC-002", True)] if stage else [("LC-" + suffix, True)]
            for case_id, complete in seeds:
                if not db.execute("SELECT id FROM cases WHERE id=?", (case_id,)).fetchone():
                    s = snapshot(case_id, customer, complete)
                    insert_case(db, s, {role: group[role] for role in ROLES}, {"id": group["coverage"], "role": "coverage"})
            for s, members in departments.seeds(customer, group):
                if not db.execute("SELECT 1 FROM cases WHERE id=?", (s["case_id"],)).fetchone():
                    owner = departments.analyst(departments.profile(s))
                    insert_case(db, s, members, {"id": members[owner], "role": owner})
