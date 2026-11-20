#!/usr/bin/env python3
"""
D1: prove the policy-drift gate refuses to run against a policy that is not the
committed one -- without modifying the live policy.

  python3 scripts/drift_gate_test.py

Anyone holding the team key can PUT /policy, including through the /team-policy web
workbench, so evidence is only meaningful when tied to a verified policy hash. The
honest way to test that gate is NOT to weaken the live department mid-build: it is to
tamper with a COPY of the committed policy file and show that both gates refuse.

Three assertions:

  1. `verify_policy.py --policy-file <tampered>` exits non-zero and reports DRIFT.
  2. `run_checks.py --policy-file <tampered>` refuses to start, so no evidence row can
     ever be written under a policy label that was not in force.
  3. The live policy hash is identical before and after this test. Nothing was PUT.

The tamper is a single loosened action: PASSPORT local -> placeholder, which would send
a government identity document to the cloud model pseudonymised instead of keeping it
inside the bank. Exactly the kind of quiet change this gate exists to catch.

Exit codes: 0 both gates held and the live policy is untouched, 1 otherwise.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brane_client as bc  # noqa: E402

HELD, BYPASSED, UNVERIFIED = "PASS", "FAIL", "UNVERIFIED"
SOURCE = bc.REPO_ROOT / "policy" / "hardened-v2.json"
TAMPER = ("PASSPORT", "local", "placeholder")


def live_hash() -> str:
    status, _h, body, raw = bc.request("GET", "/policy", timeout=30.0)
    if status != "200" or not isinstance(body, dict):
        raise RuntimeError(f"GET /policy -> HTTP {status}: {bc.scrub(raw)[:200]}")
    return bc.policy_hash(body)


def run(cmd) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *cmd], cwd=bc.REPO_ROOT,
                          capture_output=True, text=True, timeout=300)


def main() -> int:
    bc.load_env()
    label, frm, to = TAMPER

    before = live_hash()
    print(f"[live] policy before the test: {before}")

    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert doc["categories"][label] == frm, f"{label} is not {frm} in the committed policy"
    doc["categories"][label] = to
    doc.setdefault("_meta", {})["policyVersion"] = "TAMPERED-hardened-v2"
    tampered_hash = bc.policy_hash({k: v for k, v in doc.items() if k != "_meta"})

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tampered-hardened-v2.json"
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        rel = str(path)
        print(f"[tamper] {label}: {frm} -> {to}  (file hash {tampered_hash})")
        print(f"[tamper] written to a temporary file only; the live policy is NOT touched\n")

        v = run(["scripts/verify_policy.py", "--policy-file", rel])
        drift_reported = v.returncode == 1 and "DRIFT" in (v.stdout + v.stderr)
        results.append((
            "D1a", "verify_policy.py refuses a tampered policy file",
            HELD if drift_reported else BYPASSED,
            f"exit={v.returncode}, DRIFT reported={'DRIFT' in v.stdout}; "
            f"{[l for l in v.stdout.splitlines() if 'DRIFT' in l or 'live =' in l or 'file =' in l][:3]}",
        ))

        r = run(["scripts/run_checks.py", "--label", "tampered", "--policy-file", rel,
                 "--runs", "1", "--only", "T1"])
        aborted = r.returncode == 1 and "[ABORT]" in (r.stdout + r.stderr)
        wrote_rows = "[wrote]" in r.stdout
        results.append((
            "D1b", "run_checks.py refuses to start on drift",
            HELD if (aborted and not wrote_rows) else BYPASSED,
            f"exit={r.returncode}, ABORT={'[ABORT]' in r.stdout}, wrote evidence={wrote_rows}; "
            f"{[l.strip() for l in r.stdout.splitlines() if 'ABORT' in l or 'hash' in l][:3]}",
        ))

    after = live_hash()
    untouched = after == before
    results.append((
        "D1c", "the live policy was never modified by this test",
        HELD if untouched else BYPASSED,
        f"before={before} after={after}",
    ))

    print("=== results ===")
    for cid, what, verdict, detail in results:
        mark = {HELD: "HELD", BYPASSED: "BYPASS", UNVERIFIED: "UNVR"}[verdict]
        print(f"  [{mark:6}] {cid} {what}")
        print(f"           {detail[:160]}")

    team = (bc.team_build().split("/")[0] or "Redwood").strip()
    stamp = bc.utc_stamp()
    out = bc.REPO_ROOT / "evidence" / f"{team.lower()}-drift-gate_{stamp}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Test ID", "Scenario type", "Expected result", "Synthetic input",
                    "Observed", "Pass/Fail", "Team / Policy version"])
        for cid, what, verdict, detail in results:
            w.writerow([
                cid, "Policy drift gate (offline)",
                "PASS = the gate HELD and refused. FAIL = evidence could be produced against "
                f"a policy that was not the committed one. Tamper: {label} {frm} -> {to}",
                f"tampered copy of policy/hardened-v2.json in a temp file "
                f"(file hash {tampered_hash}); live policy untouched",
                detail, verdict, f"{team} / drift-gate / live {before}",
            ])
    print(f"\n[wrote] {bc.rel(out)}")

    bad = [r for r in results if r[2] != HELD]
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
