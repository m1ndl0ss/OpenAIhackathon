"""Rehearse the two revisions through the staff API using a new, temporary bank database."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi.testclient import TestClient

from backend import brane_client
from backend.demo import make_principals
from backend.main import create_app
from backend.store import DESKS
from scripts.brane_client import ASSIGNED_BASE, load_env
from tools.agent_utility import EXPECTATIONS, check_packets

CASE = "/v2/trade/cases/LC-001"
MARKER = "review.contact@example.invalid"
PARTY_NAMES = ("Robin Example", "R. Example")
NOTE = (f"Synthetic supplier contact {PARTY_NAMES[0]} ({MARKER}). "
        f"Invoice register contact {PARTY_NAMES[1]} ({MARKER}).")


class OutboundCheck:
    """Observe urllib before transport. Retain counts only. Stop on a private case field."""

    def __init__(self):
        self.requests = Counter()
        self.marker_hits = 0
        self.active = True

    def __call__(self, event, args):
        if not self.active or event != "urllib.Request":
            return
        url, body, _, method = args
        if url not in (ASSIGNED_BASE + "/policy", ASSIGNED_BASE + "/chat/completions"):
            raise RuntimeError("Unexpected network destination during rehearsal")
        self.requests[f"{method} {urlsplit(url).path}"] += 1
        if body:
            self.marker_hits += sum(body.count(value.encode()) for value in (
                MARKER, *PARTY_NAMES, "ORG_DEMO_01", "FAC-USD-01", "DOC-INV-01", "200000000", "50000000",
            ))
            if self.marker_hits:
                raise RuntimeError("A private field reached the rehearsal transport boundary")


def rehearsal(client, principals, mode):
    tokens = {staff["role"]: token for token, staff in principals.items()}
    runs = []

    def call(role, path="", body=None, expected=None):
        headers = {"Authorization": "Bearer " + tokens[role]}
        if body is None:
            response = client.get(CASE + path, headers=headers)
        else:
            headers["Idempotency-Key"] = uuid4().hex
            response = client.post(CASE + path, json=body, headers=headers)
        if not (response.is_success if expected is None else response.status_code == expected):
            raise RuntimeError(f"{role} {path or 'case'} returned HTTP {response.status_code}")
        return response.json()

    def prepare(revision):
        started = perf_counter()
        submitted = call("coverage", "/runs", {"revision": revision, "mode": mode}, 202)
        run = call("coverage", "/runs/" + submitted["run_id"])
        if run["status"] != "sealed":
            raise RuntimeError(f"Revision {revision}: {run['status']} ({run['analysis']['reason']})")
        packets = {}
        observations = []
        for desk in DESKS:
            file = call(desk)
            packets[desk], = file["packets"]
            observations.extend(file["last_run"]["analysis"]["observations"])
        observed, refs, problems = check_packets(packets, EXPECTATIONS[revision])
        if problems:
            raise RuntimeError(f"Revision {revision} did not match the case answer key: {', '.join(problems)}")
        if mode == "live" and (not observations or any(
                not item.get("policy_hash") or not item.get("provider_request_id") for item in observations)):
            raise RuntimeError("Missing policy readback or model request ID")
        usage = [item.get("usage", {}).get("total_tokens") for item in observations]
        runs.append({
            "case_id": run["case_id"], "revision": revision, "run_id": run["run_id"],
            "status": run["status"], "mode": mode, "policy_version": run["analysis"]["policy_version"],
            "packet_hash": file["packet_hash"], "expected": EXPECTATIONS[revision], "observed": observed,
            "citation_checks": refs, "verdict": "pass", "observations": observations,
            "model_calls": run["analysis"]["model_calls"], "tool_reads": run["analysis"]["tool_reads"],
            "total_tokens": sum(usage) if usage and all(type(n) is int for n in usage) else None,
            "elapsed_seconds": round(perf_counter() - started, 3),
        })
        return {"revision": revision, "packet_hash": file["packet_hash"]}

    def sign(desk, binding, disposition="clear", **fields):
        return call(desk, "/reviews/" + desk, {
            **binding, "disposition": disposition, "reason_code": "CHECKS_COMPLETE",
            "reason": f"{desk} reviewed the synthetic case evidence.",
            "expected_review_event_id": None, **fields,
        })

    # This note is bank-local across both model runs, including both occurrences of the synthetic contact.
    call("coverage", "/requests", {"revision": 1, "to_desk": "trade_finance", "question": NOTE})
    if not any(q["question"] == NOTE for q in call("trade_finance")["requests"]):
        raise RuntimeError("Trade Finance did not receive the bank-local contact note")
    first = prepare(1)
    sign("credit_risk", first)
    sign("compliance", first, "hold", reason_code="DOCUMENT_REQUIRED", request_to="coverage",
         required_evidence="supplier_invoice")
    held = call("coverage")
    decision = {"decision": "approve", "reason": "Three current desk findings and the delegated mandate checked."}
    denied = call("final_officer", "/decision", {**first, **decision}, 409)
    if held["status"] != "on_hold" or held["receipt"] is not None:
        raise RuntimeError("Expected an open hold with no issuance")
    request = next(q for q in held["requests"] if q["from_desk"] == "compliance")
    call("coverage", "/evidence", {"expected_revision": 1, "fixture_document_id": "DOC-INV-01",
                                   "request_id": request["request_id"], "note": NOTE})
    if not any(q["reply"] == NOTE for q in call("compliance")["requests"]):
        raise RuntimeError("Compliance did not receive the bank-local invoice note")
    second = prepare(2)
    sign("trade_finance", second)
    sign("credit_risk", second)
    sign("compliance", second, resolves_hold_ids=[held["holds"][0]["hold_id"]], evidence_ref="DOC-INV-01@1")
    ready = call("final_officer")
    stale = call("final_officer", "/decision", {**first, **decision}, 409)
    call("final_officer", "/decision", {**second, **decision})
    receipt = call("operations", "/issuance", second)
    repeat = call("operations", "/issuance", second)
    terminal = call("operations")
    actions = Counter(row["action"] for row in call("operations", "/audit"))
    if (ready["status"] != "ready_for_decision" or terminal["status"] != "issued_simulated"
            or repeat["receipt_id"] != receipt["receipt_id"] or actions["receipt.issued"] != 1
            or actions["decision.approve"] != 1):
        raise RuntimeError("Decision or receipt did not match the answer key")
    return {"runs": runs, "workflow": {
        "hold": held["status"], "decision_while_held": {"http": 409, "reason": denied["code"]},
        "decision_on_old_revision": {"http": 409, "reason": stale["code"]},
        "current_signatures": [{k: row[k] for k in ("desk", "actor_id", "disposition", "revision")}
                               for row in ready["reviews"]],
        "state_before_final_decision": ready["status"], "final_decision_role": "final_officer",
        "decision_events": actions["decision.approve"], "receipt_events": actions["receipt.issued"],
        "receipt_id": receipt["receipt_id"], "final_state": terminal["status"],
    }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["live", "fixture"], default="live")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "live":
        load_env()
        brane_client.live_run_config()
    path = args.output or Path(f".clearance/evidence/submission-{args.mode}.json")
    principals = make_principals()
    observer = OutboundCheck()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sys.addaudithook(observer)
    try:
        with TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "case.sqlite3", principals, mode=args.mode)
            with TestClient(app) as client:
                result = rehearsal(client, principals, args.mode)
    finally:
        observer.active = False
    calls = sum(run["model_calls"] for run in result["runs"])
    if args.mode == "live" and observer.requests["POST /api/v1/chat/completions"] != calls:
        raise RuntimeError("Outgoing model requests did not reconcile with case telemetry")
    result.update({
        "started_utc": started, "mode": args.mode, "answer_key": "legal/case-answer-key.md",
        "participants": "Scripted actions with six separate synthetic staff identities through the staff API.",
        "transport": {"scope": "Python urllib audit event at the bank before transmission to BRANE.",
                      "requests": dict(observer.requests), "matching_private_fields": observer.marker_hits,
                      "email_occurrences_per_note": NOTE.count(MARKER), "name_forms_per_note": len(PARTY_NAMES),
                      "notes_verified_in_entitled_desk_views": 2},
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{args.mode} · both revisions passed · {calls} model turns · one simulated receipt · {path}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
