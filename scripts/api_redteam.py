#!/usr/bin/env python3
"""
Red team against the bank application, not the firewall.

  python3 scripts/api_redteam.py
  python3 scripts/api_redteam.py --only Y4,Y7

scripts/redteam_suite.py attacks BRANE and our own masking. This attacks the half
of the gate BRANE cannot defend: case and desk isolation (A1), the human-approval
invariants (A3) and revision/duplicate finalisation (A4). Those three were marked
unverified in evidence/REPORT.md because they live in Nikita's API; this runs real
requests against the real app over a throwaway SQLite database.

Same verdict convention as the BRANE suite, because it inverts the usual reading:

  PASS = the control HELD. The attack did not get what it wanted.
  FAIL = the control was BYPASSED. A finding.
  UNVERIFIED = not enough was observable to say.

Nothing here touches the live BRANE policy: every run is CLEARANCE_MODE=fixture on
a temporary database, so the suite is safe to run during a demo.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import secrets
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import brane_client as bc  # noqa: E402

HELD, BYPASSED, UNVERIFIED = "PASS", "FAIL", "UNVERIFIED"
CASES = "/v2/trade/cases"
STAGE = f"{CASES}/LC-001"      # staged file: Compliance hold open, invoice missing
COMPLETE = f"{CASES}/LC-002"   # complete file
DESKS = ("trade_finance", "credit_risk", "compliance")


# ----------------------------------------------------------------------------------
# Harness
# ----------------------------------------------------------------------------------
class Bank:
    """A fresh app + database per attack, so no attack can contaminate another."""

    def __init__(self):
        from fastapi.testclient import TestClient

        from backend.demo import make_principals
        from backend.main import create_app

        os.environ["CLEARANCE_MODE"] = "fixture"
        self.principals = make_principals()
        sample = next(iter(self.principals.values()))
        self.customer = sample["customer_ref"]

        # A SECOND customer with its own six desks, which is what spec A1 asks for
        # ("give the isolation test a different customer"). The delivered
        # make_principals() puts every staff member on one customer_ref, and
        # grouped_assignments() requires six distinct roles per customer, so a lone
        # outsider is rejected before the app starts.
        self.outsider_tokens: Dict[str, str] = {}
        for role in ("coverage", *DESKS, "final_officer", "operations"):
            token = secrets.token_urlsafe(32)
            self.principals[token] = {
                "id": f"staff-rt-{role}",
                "name": f"Outsider {role.replace('_', ' ').title()}",
                "role": role,
                "customer_ref": "ORG_DEMO_99",
            }
            self.outsider_tokens[role] = token
        self.outsider_token = self.outsider_tokens["coverage"]

        self.tokens = {
            p["role"]: t for t, p in self.principals.items()
            if p.get("customer_ref") == self.customer
        }
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "attack.sqlite3"
        self.client = TestClient(create_app(path, self.principals))
        self.client.__enter__()

    def close(self):
        try:
            self.client.__exit__(None, None, None)
        finally:
            self._tmp.cleanup()

    def h(self, role_or_token, key=None):
        token = self.tokens.get(role_or_token, role_or_token)
        out = {"Authorization": f"Bearer {token}"}
        out["Idempotency-Key"] = key or str(uuid4())
        return out

    def post(self, path, role, body, key=None):
        return self.client.post(path, json=body, headers=self.h(role, key))

    def get(self, path, role="coverage"):
        return self.client.get(path, headers=self.h(role))

    def case(self, path=STAGE, role="coverage"):
        return self.get(path, role).json()

    def seal(self, path=STAGE):
        """Drive the documented happy path far enough to get a sealed packet."""
        rev = self.case(path)["revision"]
        run = self.post(path + "/runs", "coverage", {"revision": rev, "mode": "fixture"})
        if run.status_code != 202:
            raise RuntimeError(f"seal failed: {run.status_code} {run.text[:200]}")
        run_id = run.json()["run_id"]
        self.get(path + f"/runs/{run_id}")
        detail = self.case(path)
        return detail, run_id

    def binding(self, path=STAGE):
        c = self.case(path)
        return {"revision": c["revision"], "packet_hash": c["packet_hash"]}

    def sign(self, desk, path=STAGE, disposition="clear", as_role=None, extra=None):
        # The workflow only accepts CHECKS_COMPLETE for a clearance and one of
        # DOCUMENT_REQUIRED / MANUAL_REVIEW / FACILITY_EXCEPTION for a hold. Sending
        # anything else returns 422 before the invariant under attack is reached,
        # which would make every verdict meaningless.
        body = {
            **self.binding(path),
            "disposition": disposition,
            "reason": "Synthetic red-team clearance recorded for attack evidence.",
            "reason_code": "CHECKS_COMPLETE" if disposition == "clear" else "DOCUMENT_REQUIRED",
        }
        body.update(extra or {})
        return self.post(f"{path}/reviews/{desk}", as_role or desk, body)

    # --- state readers, used for preconditions and assertions ---
    def reviews(self, path=STAGE):
        return self.case(path).get("reviews") or []

    def cleared_desks(self, path=STAGE):
        return {r["desk"] for r in self.reviews(path)
                if r.get("disposition") == "clear" and r["desk"] in DESKS}

    def open_holds(self, path=STAGE):
        return [h for h in (self.case(path).get("holds") or [])
                if not h.get("resolved_event")]

    def decision(self, path=STAGE):
        return self.case(path).get("decision")

    def receipt(self, path=STAGE):
        return self.case(path).get("receipt")


class SetupFailed(Exception):
    """The attack could not reach the state it exists to test."""


def need(condition, what: str):
    """
    Guard a precondition. An attack that never reaches its own scenario proves
    nothing, and silently passes -- which is exactly how the first version of this
    suite reported four HELDs for requests that were rejected at validation.
    """
    if not condition:
        raise SetupFailed(what)


@dataclass
class Attack:
    aid: str
    family: str
    goal: str
    run: Callable[[Bank], Tuple[str, str]]
    rationale: str


def denied(resp) -> bool:
    return resp.status_code in (401, 403, 404, 409, 412, 422)


# ----------------------------------------------------------------------------------
# Attacks
# ----------------------------------------------------------------------------------
def y1_cross_customer_read(bank: Bank):
    r = bank.get(STAGE, bank.outsider_token)
    if denied(r):
        return (HELD, f"outsider read refused with HTTP {r.status_code} "
                      f"(uniform response, no case detail disclosed)")
    body = r.text[:160]
    return (BYPASSED, f"an actor for a different customer read the case: HTTP {r.status_code} {body}")


def y2_unauthenticated(bank: Bank):
    r = bank.client.get(STAGE)
    w = bank.client.post(f"{STAGE}/decision", json={"revision": 1, "packet_hash": "0" * 64,
                                                    "decision": "approve", "reason": "no auth at all"})
    if denied(r) and denied(w):
        return (HELD, f"unauthenticated read {r.status_code} and write {w.status_code} both refused")
    return (BYPASSED, f"unauthenticated access allowed: read {r.status_code}, write {w.status_code}")


def y3_wrong_desk_signature(bank: Bank):
    detail, _ = bank.seal()
    need(detail.get("packet_hash"), "no packet was sealed, so no clearance could be signed")
    r = bank.sign("compliance", as_role="credit_risk")
    if denied(r):
        return (HELD, f"credit_risk signing the compliance desk refused with HTTP {r.status_code}")
    return (BYPASSED, f"a desk signed another desk's clearance: HTTP {r.status_code} {r.text[:120]}")


def y4_decide_with_open_hold(bank: Bank):
    """
    A3: Trade and Credit clear while an independent Compliance hold stays open.
    Approval must remain blocked.

    This uses the COMPLETE fixture, not the staged one: LC-001 refuses every
    clearance with evidence_incomplete until the invoice is supplied, so the
    "cleared desks plus an open hold" state cannot exist there at all.
    """
    detail, _ = bank.seal(COMPLETE)
    need(detail.get("packet_hash"), "no packet was sealed")
    for d in ("trade_finance", "credit_risk"):
        resp = bank.sign(d, COMPLETE)
        need(resp.status_code == 201,
             f"{d} clearance was not recorded ({resp.status_code} {resp.text[:140]})")
    hold = bank.sign("compliance", COMPLETE, disposition="hold",
                     extra={"reason_code": "MANUAL_REVIEW"})
    need(hold.status_code == 201,
         f"the independent Compliance hold was not recorded ({hold.status_code} "
         f"{hold.text[:140]})")
    need(bank.cleared_desks(COMPLETE) == {"trade_finance", "credit_risk"},
         f"expected exactly two clearances, got {sorted(bank.cleared_desks(COMPLETE))}")
    need(bank.open_holds(COMPLETE), "no open hold present, so the invariant is not under test")

    r = bank.post(f"{COMPLETE}/decision", "final_officer",
                  {**bank.binding(COMPLETE), "decision": "approve",
                   "reason": "Red-team approval attempt with an unresolved Compliance hold."})
    case = bank.case(COMPLETE)
    if denied(r) and not case.get("decision") and not case.get("receipt"):
        return (HELD, f"approval refused with HTTP {r.status_code} while a Compliance hold was "
                      f"open; status={case.get('status')}, decision=None, receipt=None")
    return (BYPASSED, f"approved with an open Compliance hold: HTTP {r.status_code}, "
                      f"decision={case.get('decision')}, receipt={case.get('receipt')}")


def y5_decide_without_all_clearances(bank: Bank):
    detail, _ = bank.seal(COMPLETE)
    need(detail.get("packet_hash"), "no packet was sealed")
    first = bank.sign("trade_finance", COMPLETE)
    need(first.status_code == 201, f"the single clearance was not recorded ({first.status_code})")
    need(bank.cleared_desks(COMPLETE) == {"trade_finance"},
         f"expected exactly one clearance, got {sorted(bank.cleared_desks(COMPLETE))}")
    r = bank.post(f"{COMPLETE}/decision", "final_officer",
                  {**bank.binding(COMPLETE), "decision": "approve",
                   "reason": "Red-team approval attempt with only one desk clearance."})
    if denied(r):
        return (HELD, f"approval with 1 of 3 clearances refused with HTTP {r.status_code}")
    return (BYPASSED, f"approved with only one desk clearance: HTTP {r.status_code}")


def y6_double_signature(bank: Bank):
    bank.seal(COMPLETE)
    first = bank.sign("credit_risk", COMPLETE)
    need(first.status_code == 201,
         f"the FIRST clearance was rejected ({first.status_code} {first.text[:140]}), so a "
         f"repeat proves nothing")
    second = bank.sign("credit_risk", COMPLETE)
    rows = [r for r in bank.reviews(COMPLETE)
            if r["desk"] == "credit_risk" and r.get("disposition") == "clear"]
    quorum = bank.cleared_desks(COMPLETE)
    if denied(second) and len(rows) == 1:
        return (HELD, f"the repeat signature was refused ({second.status_code}) and credit_risk "
                      f"is recorded once; quorum={sorted(quorum)}")
    if len(quorum) == 1:
        return (HELD, f"the repeat returned {second.status_code} but credit_risk still counts as "
                      f"one desk ({len(rows)} review rows, quorum={sorted(quorum)}), so a single "
                      f"reviewer cannot manufacture the three-desk quorum")
    return (BYPASSED, f"one desk produced a quorum of {sorted(quorum)} by signing "
                      f"{len(rows)} times")


def y7_concurrent_decisions(bank: Bank):
    """A4: two valid finalisations at once must leave one durable outcome."""
    bank.seal(COMPLETE)
    for d in DESKS:
        resp = bank.sign(d, COMPLETE)
        need(resp.status_code == 201,
             f"{d} clearance was not recorded ({resp.status_code} {resp.text[:120]})")
    need(bank.cleared_desks(COMPLETE) == set(DESKS),
         f"quorum incomplete: {sorted(bank.cleared_desks(COMPLETE))}")
    body = {**bank.binding(COMPLETE), "decision": "approve",
            "reason": "Red-team concurrent finalisation attempt, distinct retry keys."}

    def fire(_i):
        return bank.post(f"{COMPLETE}/decision", "final_officer", body, key=str(uuid4()))

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(fire, range(2)))
    codes = [r.status_code for r in responses]
    created = sum(1 for r in responses if r.status_code in (200, 201))
    audit = bank.get(f"{COMPLETE}/audit", "coverage").json()
    events = audit if isinstance(audit, list) else (audit.get("events") or [])
    finals = [e for e in events if "decision" in json.dumps(e).lower()]
    decision = bank.decision(COMPLETE)
    receipts = 1 if bank.receipt(COMPLETE) else 0
    if not decision:
        return (UNVERIFIED, f"neither finalisation was recorded (codes={codes}); the race was "
                            f"not exercised")
    if created <= 1 and receipts <= 1:
        return (HELD, f"two concurrent finalisations with distinct retry keys left ONE durable "
                      f"outcome: codes={codes}, accepted={created}, decision events={len(finals)}, "
                      f"receipts={receipts}")
    return (BYPASSED, f"concurrent finalisation produced {created} accepted responses, "
                      f"{len(finals)} decision events and {receipts} receipts: codes={codes}")


def y8_issuance_without_decision(bank: Bank):
    bank.seal(COMPLETE)
    for d in DESKS:
        resp = bank.sign(d, COMPLETE)
        need(resp.status_code == 201, f"{d} clearance was not recorded ({resp.status_code})")
    need(bank.cleared_desks(COMPLETE) == set(DESKS),
         f"quorum incomplete: {sorted(bank.cleared_desks(COMPLETE))}")
    early = bank.post(f"{COMPLETE}/issuance", "operations", bank.binding(COMPLETE))
    if not denied(early):
        return (BYPASSED, f"Operations issued a receipt with no officer decision: "
                          f"HTTP {early.status_code}")
    decision = bank.post(f"{COMPLETE}/decision", "final_officer",
                         {**bank.binding(COMPLETE), "decision": "approve",
                          "reason": "Red-team approval to reach the issuance step."})
    need(decision.status_code in (200, 201) and bank.decision(COMPLETE),
         f"the approval itself was refused ({decision.status_code} {decision.text[:140]}), so the "
         f"issuance path was never reached")
    first = bank.post(f"{COMPLETE}/issuance", "operations", bank.binding(COMPLETE))
    second = bank.post(f"{COMPLETE}/issuance", "operations", bank.binding(COMPLETE))
    accepted = [r.status_code for r in (first, second) if r.status_code in (200, 201)]
    receipt = bank.receipt(COMPLETE)
    # Identify the receipt so a second accepted response can be told apart from a
    # second receipt. The spec invariant is "at most one simulated issuance receipt".
    def ident(resp):
        try:
            body = resp.json()
        except Exception:
            return None
        if not isinstance(body, dict):
            return None
        for key in ("receipt_id", "receipt", "event_id", "id"):
            if body.get(key):
                return json.dumps(body[key], sort_keys=True)
        return None

    ids = [ident(first), ident(second)]
    distinct = {i for i in ids if i}
    if receipt and len(distinct) <= 1:
        return (HELD, f"issuance refused before the decision ({early.status_code}); afterwards "
                      f"two calls with distinct retry keys returned {accepted} but produced ONE "
                      f"receipt (identities={sorted(distinct)}), so the second was an idempotent "
                      f"replay rather than a new issuance")
    if not receipt:
        return (UNVERIFIED, f"no receipt is recorded on the case after {accepted}; the invariant "
                            f"was not exercised")
    return (BYPASSED, f"two distinct issuance receipts were created: {sorted(distinct)} "
                      f"(responses {accepted})")


def y9_stale_clearance(bank: Bank):
    """
    A4: a material amendment must invalidate anything bound to the previous packet.

    The staged file refuses clearances until the invoice arrives, so the attack binds
    to the pre-amendment packet, lets Coverage supply the invoice (which creates a new
    revision), and then replays the stale binding.
    """
    detail, _ = bank.seal()
    need(detail.get("packet_hash"), "no packet was sealed")
    before = bank.binding()

    supplied = bank.post(f"{STAGE}/evidence", "coverage",
                         {"expected_revision": before["revision"],
                          "fixture_document_id": "DOC-INV-01"})
    need(supplied.status_code in (200, 201),
         f"the invoice was not accepted ({supplied.status_code} {supplied.text[:140]})")
    after = bank.binding()
    need(after["revision"] != before["revision"] or after["packet_hash"] != before["packet_hash"],
         f"the amendment produced no new revision or packet "
         f"(rev {before['revision']} -> {after['revision']})")

    replay = bank.post(f"{STAGE}/reviews/trade_finance", "trade_finance",
                       {**before, "disposition": "clear",
                        "reason": "Red-team replay of a binding captured before the amendment.",
                        "reason_code": "CHECKS_COMPLETE"})
    if denied(replay):
        return (HELD, f"a clearance bound to the pre-amendment packet was refused with HTTP "
                      f"{replay.status_code} (revision {before['revision']} -> "
                      f"{after['revision']}, packet changed="
                      f"{before['packet_hash'] != after['packet_hash']})")
    return (BYPASSED, f"a stale binding was accepted after a material amendment: HTTP "
                      f"{replay.status_code}")


def y10_role_escalation_via_body(bank: Bank):
    """Can a desk actor smuggle a role or desk through the request body?"""
    detail, _ = bank.seal(COMPLETE)
    need(detail.get("packet_hash"), "no packet was sealed")
    attempts = {
        "extra desk field": {**bank.binding(COMPLETE), "disposition": "clear",
                             "reason": "Red-team role smuggling attempt via body.",
                             "reason_code": "CHECKS_COMPLETE", "desk": "final_officer"},
        "extra role field": {**bank.binding(COMPLETE), "disposition": "clear",
                             "reason": "Red-team role smuggling attempt via body.",
                             "reason_code": "CHECKS_COMPLETE", "role": "final_officer"},
        "extra actor field": {**bank.binding(COMPLETE), "disposition": "clear",
                              "reason": "Red-team role smuggling attempt via body.",
                              "reason_code": "CHECKS_COMPLETE", "actor": "final_officer"},
    }
    results = {}
    for label, body in attempts.items():
        r = bank.post(f"{COMPLETE}/reviews/credit_risk", "credit_risk", body)
        results[label] = r.status_code
    if all(code in (401, 403, 404, 409, 412, 422) for code in results.values()):
        return (HELD, f"every unknown body field was rejected outright: {results} "
                      f"(the models forbid extra fields)")
    accepted = {k: v for k, v in results.items() if v in (200, 201)}
    decision_reached = bank.post(f"{COMPLETE}/decision", "credit_risk",
                                 {**bank.binding(COMPLETE), "decision": "approve",
                                  "reason": "Red-team escalation check after body smuggling."})
    if denied(decision_reached):
        return (HELD, f"body fields accepted {accepted} but role enforcement still refused the "
                      f"decision ({decision_reached.status_code})")
    return (BYPASSED, f"a desk actor reached the officer decision: {decision_reached.status_code}")


def build_attacks() -> List[Attack]:
    return [
        Attack("Y1", "isolation (A1)", "read another customer's case",
               y1_cross_customer_read,
               "Spec A1: each user sees only assigned cases, and an unavailable resource must "
               "give a uniform response that does not confirm the case exists."),
        Attack("Y2", "isolation (A1)", "act with no session at all", y2_unauthenticated,
               "The cheapest attack there is. Worth evidencing rather than assuming."),
        Attack("Y3", "isolation (A1)", "sign a desk you do not own", y3_wrong_desk_signature,
               "Three distinct desk clearances only mean something if a desk cannot sign for "
               "another."),
        Attack("Y4", "approval (A3)", "approve while a Compliance hold is open",
               y4_decide_with_open_hold,
               "Spec A3: positive approval and issuance stay blocked until the owning desk "
               "resolves its hold. This is the invariant the demo is built around."),
        Attack("Y5", "approval (A3)", "approve with one clearance instead of three",
               y5_decide_without_all_clearances,
               "The mandate requires three distinct current-version clearances before the "
               "officer decides."),
        Attack("Y6", "approval (A3)", "sign the same desk twice to fake a quorum",
               y6_double_signature,
               "If one desk can sign twice and each counts, a single reviewer manufactures the "
               "three-desk quorum by themselves."),
        Attack("Y7", "duplication (A4)", "two concurrent finalisations, two outcomes",
               y7_concurrent_decisions,
               "Spec A4: concurrent valid submissions must leave one durable final outcome and "
               "at most one receipt. Distinct retry keys, so idempotency keys alone will not "
               "save it."),
        Attack("Y8", "duplication (A4)", "issue with no decision, then issue twice",
               y8_issuance_without_decision,
               "Issuance is a separate Operations command. It must require the decision and "
               "must produce exactly one receipt."),
        Attack("Y9", "revision (A4)", "replay a clearance signed before an amendment",
               y9_stale_clearance,
               "A material amendment invalidates prior approvals. Replaying the old packet hash "
               "is how that invariant gets tested."),
        Attack("Y10", "isolation (A1)", "smuggle a role through the request body",
               y10_role_escalation_via_body,
               "Model content must never choose a mandate or reviewer. Extra body fields are "
               "the first place an attacker looks."),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Red team the bank application (A1, A3, A4).")
    ap.add_argument("--only", help="comma-separated attack ids")
    ap.add_argument("--runs", type=int, default=1,
                    help="repeat each attack; concurrency attacks benefit from more")
    args = ap.parse_args()

    attacks = build_attacks()
    if args.only:
        want = {x.strip() for x in args.only.split(",")}
        attacks = [a for a in attacks if a.aid in want]

    bc.load_env()
    team = (bc.team_build().split("/")[0] or "Redwood").strip()
    code_rev = os.popen("git rev-parse --short HEAD").read().strip() or "unknown"
    print(f"[target] backend.main:create_app, CLEARANCE_MODE=fixture, temp SQLite per attack")
    print(f"[target] code revision {code_rev}")
    print(f"[plan]   {len(attacks)} attacks x {args.runs} run(s)\n")

    stamp = bc.utc_stamp()
    csv_path = bc.REPO_ROOT / "evidence" / f"{team.lower()}-api-redteam_{stamp}.csv"
    jsonl_path = bc.REPO_ROOT / "evidence" / "raw" / f"{team.lower()}-api-redteam_{stamp}.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    tally: Dict[str, int] = {HELD: 0, BYPASSED: 0, UNVERIFIED: 0}
    per_attack: Dict[str, set] = {}

    with csv_path.open("w", newline="", encoding="utf-8") as cf, \
         jsonl_path.open("w", encoding="utf-8") as jf:
        w = csv.writer(cf)
        w.writerow(["Test ID", "Scenario type", "Expected result", "Synthetic input",
                    "Observed", "Verdict reason", "Pass/Fail", "Code revision", "Team"])
        for a in attacks:
            for i in range(1, args.runs + 1):
                bank = Bank()
                try:
                    verdict, reason = a.run(bank)
                except SetupFailed as exc:
                    verdict = UNVERIFIED
                    reason = f"setup did not reach the state under test: {exc}"
                except Exception as exc:  # an attack that crashes proves nothing
                    verdict = UNVERIFIED
                    reason = f"attack harness error: {type(exc).__name__}: {exc}"
                finally:
                    bank.close()
                tally[verdict] += 1
                per_attack.setdefault(a.aid, set()).add(verdict)
                mark = {HELD: "HELD", BYPASSED: "BYPASS", UNVERIFIED: "UNVR"}[verdict]
                print(f"  [{mark:6}] {a.aid:4} {a.family:16} run {i}: {reason[:108]}")
                w.writerow([a.aid, f"Red team · {a.family}",
                            f"PASS = control HELD. FAIL = BYPASSED (finding). Goal: {a.goal}",
                            "synthetic fixture case LC-001/LC-002, throwaway SQLite",
                            reason[:400], reason, verdict, code_rev, team])
                jf.write(json.dumps({
                    "attack_id": a.aid, "family": a.family, "goal": a.goal,
                    "rationale": a.rationale, "run_index": i,
                    "timestamp_utc": bc.utc_iso(), "code_revision": code_rev,
                    "backend_mode": "fixture", "verdict": verdict, "verdict_reason": reason,
                }, ensure_ascii=False) + "\n")

    print(f"\n[total] {tally[HELD]} held, {tally[BYPASSED]} bypassed, {tally[UNVERIFIED]} unverified")
    print("\n=== per attack ===")
    for aid, vs in per_attack.items():
        v = next(iter(vs)) if len(vs) == 1 else f"INCONSISTENT {sorted(vs)}"
        print(f"  {aid:4} {{'PASS': 'held', 'FAIL': 'BYPASSED', 'UNVERIFIED': 'unverified'}}".format()
              if False else f"  {aid:4} " + {HELD: "held", BYPASSED: "BYPASSED",
                                             UNVERIFIED: "unverified"}.get(v, v))
    print(f"\n[wrote] {bc.rel(csv_path)}")
    print(f"[wrote] {bc.rel(jsonl_path)}")
    return 0 if tally[BYPASSED] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
