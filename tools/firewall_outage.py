"""Measure the bank's behaviour when its firewall is unreachable in an isolated process."""

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from backend.demo import make_principals
from backend.main import create_app
from scripts.brane_client import ALLOWED_HOST, ASSIGNED_BASE


def run():
    # All HTTP leaves through the monitored process. The credential is deliberately synthetic.
    for key in tuple(os.environ):
        if key.lower().endswith("_proxy"):
            del os.environ[key]
    os.environ.update(no_proxy="*", BRANE_BASE_URL=ASSIGNED_BASE, BRANE_API_KEY="outage-test-credential",
                      BRANE_POLICY_VERSION="hardened-v2", BRANE_MODEL="outage-test-model")
    requests, attempts = [], []

    def deny_network(event, args):
        if event == "urllib.Request":
            url, _, _, method = args
            location = urlsplit(url)
            requests.append({"method": method, "host": location.hostname, "path": location.path})
        if event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}:
            attempts.append({"event": event, "host": args[0]})
            raise OSError("Controlled firewall outage")
        if event in {"socket.connect", "socket.sendto", "socket.sendmsg"}:
            if args[0].family in {socket.AF_INET, socket.AF_INET6}:
                attempts.append({"event": event, "host": str(args[1])})
                raise OSError("Controlled firewall outage")

    people = make_principals()
    token = next(key for key, actor in people.items() if actor["role"] == "coverage")
    headers = {"Authorization": "Bearer " + token, "Idempotency-Key": "outage-rehearsal"}
    case = "/v2/trade/cases/LC-001"
    sys.addaudithook(deny_network)
    with TemporaryDirectory() as folder:
        with TestClient(create_app(Path(folder) / "outage.sqlite3", people, mode="live")) as client:
            submitted = client.post(case + "/runs", headers=headers, json={"revision": 1, "mode": "live"})
            submitted.raise_for_status()
            run_id = submitted.json()["run_id"]
            record = client.get(case + "/runs/" + run_id, headers=headers).json()
            file = client.get(case, headers=headers).json()
    passed = (requests == [{"method": "GET", "host": ALLOWED_HOST, "path": "/api/v1/policy"}]
              and bool(attempts) and all(attempt["host"] == ALLOWED_HOST for attempt in attempts)
              and record["status"] == "analysis_unavailable" and file["packet_hash"] is None
              and file["receipt"] is None)
    return {"check": "T5 · unavailable BRANE", "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "verdict": "PASS" if passed else "FAIL", "environment": "Isolated egress-denied Python process",
            "boundary": "Independent Python audit hook denies DNS and IP socket operations for the bank process.",
            "run_id": run_id, "mode": record["mode"], "bank_run_status": record["status"],
            "http_attempts": requests, "denied_network_attempts": attempts,
            "model_post_attempts": sum(item["method"] == "POST" for item in requests),
            "sealed": file["packet_hash"] is not None, "receipt": file["receipt"] is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".clearance/evidence/firewall-outage.json"))
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['verdict']} · {report['bank_run_status']} · {report['model_post_attempts']} model POSTs · {args.output}")
    sys.exit(0 if report["verdict"] == "PASS" else 1)
