"""Rehearse one complete synthetic file per department through the normal staff API."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from backend import departments
from backend.demo import make_principals
from backend.main import create_app
from scripts.brane_client import load_env


def rehearse(app, tokens, profile, mode):
    case_id = profile["code"] + "-001"
    analyst, approver = departments.analyst(profile), departments.approver(profile)
    root = "/v2/trade/cases/" + case_id
    record = {"workflow": profile["id"], "case_id": case_id, "bank_only": profile["local_only"]}
    with TestClient(app) as client:
        def call(role, suffix="", body=None):
            headers = {"Authorization": "Bearer " + tokens[role]}
            if body is None:
                response = client.get(root + suffix, headers=headers)
            else:
                headers["Idempotency-Key"] = uuid4().hex
                response = client.post(root + suffix, json=body, headers=headers)
            response.raise_for_status()
            return response.json()

        call(analyst, "/runs", {"revision": 1, "mode": mode})
        case = call(analyst)
        run = case["last_run"]
        analysis = run["analysis"] or {}
        observations = [{k: obs[k] for k in ("task", "route", "model", "provider_request_id", "policy_hash")
                         if obs.get(k)} for obs in analysis.get("observations", [])]
        record.update(run_id=run["run_id"], status=run["status"], policy=analysis.get("policy_version"),
                      reason=analysis.get("reason"), model_calls=analysis.get("model_calls"), observations=observations)
        if run["status"] != "sealed":
            return record
        lanes = [p["desk"] for p in case["packets"]]
        sources = {s["ref"] for s in case["sources"]}
        cited = {ref for packet in case["packets"] for ref in packet["policy_refs"] + packet["evidence_refs"]}
        record["checked_packets"] = lanes == list(departments.LANES) and cited <= sources
        if profile["local_only"]:
            record["checked_route"] = (record["model_calls"] == 0 and len(observations) == 3
                                       and all(obs["route"] == "bank_local" for obs in observations))
        else:
            required = {"direct", "local", "pseudonymized"} if mode == "live" else {"fixture"}
            record["checked_route"] = all(any(
                obs["task"] == departments.task_id(profile, lane) and obs["route"] in required
                and (mode != "live" or obs.get("policy_hash")) for obs in observations
            ) for lane in departments.LANES)
        if not record["checked_packets"] or not record["checked_route"]:
            return record
        body = {"revision": 1, "packet_hash": case["packet_hash"], "reason": "Reviewed the synthetic case for the rehearsal."}
        for role in departments.reviewers(profile):
            call(role, "/workflow-action", {**body, "action": "sign"})
        call(approver, "/workflow-action", {**body, "action": "complete"})
        final = call(approver)
        if final["status"] == "completed" and final["decision"]["actor_id"] == "staff-" + approver:
            record.update(outcome=final["status"], receipt=final["receipt"]["receipt_id"],
                          signed_reviews=len(final["reviews"]))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    parser.add_argument("--workflow", action="append", choices=departments.CURRENT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "live":
        load_env()
    profiles = [p for p in departments.CATALOG if not args.workflow or p["id"] in args.workflow]
    people = {**make_principals(), **make_principals(specialists=True)}
    tokens = {staff["role"]: token for token, staff in people.items()}
    with TemporaryDirectory() as tmp:
        app = create_app(Path(tmp) / "rehearsal.sqlite", people, mode=args.mode)
        with ThreadPoolExecutor(max_workers=3) as workers:
            records = list(workers.map(lambda p: rehearse(app, tokens, p, args.mode), profiles))
    output = args.output or Path(f".clearance/evidence/departments-{args.mode}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"observed_at": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
                                 "example": 1, "cases": records}, indent=2) + "\n")
    incomplete = [row["case_id"] + " " + row["status"] for row in records if not row.get("receipt")]
    print(f"{len(records) - len(incomplete)}/{len(records)} completed in {args.mode} mode. Results in {output}.")
    if incomplete:
        raise SystemExit(", ".join(incomplete))


if __name__ == "__main__":
    main()
