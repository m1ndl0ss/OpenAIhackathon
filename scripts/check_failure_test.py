#!/usr/bin/env python3
"""
A5 / track test 5 -- "check failure": when the protection check is unavailable, the
request is not sent, and an automatic fallback to a cloud model fails the test.

  python3 scripts/check_failure_test.py
  python3 scripts/check_failure_test.py --client raw          # the transport, uncontrolled
  python3 scripts/check_failure_test.py --client mymod:call   # Tasos's adapter

Why this file exists. The track description states test 5 as a property of the SYSTEM
under outage, not of a prompt: "if the protection check is unavailable, the request is
not sent. An automatic fallback to the cloud model fails this test." Our T5b tests an
unavailable *business* check while BRANE was healthy, so it does not evidence this. This
does.

The evidence is an INDEPENDENT observation, not the client's own logging. A
sys.addaudithook records every socket.getaddrinfo and socket.connect the process
attempts, for the whole run. A client cannot write a reassuring log line into it,
because it never passes through the client at all.

The static pre-check covers code and configuration (.py, .json, .yaml, .env, ...)
outside docs/. It deliberately does not scan prose: evidence/REPORT.md documents this
check and therefore contains the very strings it looks for. Secrets are scanned
separately across every file, prose included, before each commit.

Scenarios, each run 3 times with the same synthetic letter-of-credit prompt:

  a dns          BRANE_BASE_URL host does not resolve (brane.invalid)
  b refused      a reserved loopback port refuses the connection
  c timeout      a loopback server accepts the request and withholds its response
  d http_5xx     a local stub returns 503
  e no_header    a local stub returns HTTP 200 with a completion and NO X-Brane-Routed-To
  f control      the real BRANE endpoint, healthy -- proves the harness can still pass

A scenario PASSES only when all three hold:
  1. the outcome is `unavailable` (or the adapter's equivalent),
  2. no answer text reached the caller,
  3. the audit log shows connection attempts ONLY to the configured endpoint for that
     scenario, and none to anything else.

Scenario f inverts 1 and 2: it must produce a real outcome and an answer.

Exit codes: 0 all scenarios passed, 1 at least one failed, 2 refused to run
(static check failed, or configuration error).
"""
from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import re
import socket
import sys
import threading
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import patch
from urllib.parse import urlsplit

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import brane_client as bc

PASS, FAIL = "PASS", "FAIL"

PROMPT = (
    "Trade Finance case note for LC-001 (ORG_DEMO_01, facility FAC-USD-01). Requested "
    "instrument USD 2,000,000.00, expiry 2027-01-31, beneficiary ORG_DEMO_02 (US). "
    "Summarise the outstanding items for the desk."
)

# ----------------------------------------------------------------------------------
# 1. Independent egress observer.
#    Installed before any scenario runs. Audit hooks cannot be removed, which is what
#    we want: nothing later in the process can switch the observer off.
# ----------------------------------------------------------------------------------
_ATTEMPTS: List[Tuple[str, str, Any]] = []
_RECORDING = {"on": False}


def _audit(event: str, args) -> None:
    if not _RECORDING["on"]:
        return
    try:
        if event == "socket.getaddrinfo":
            _ATTEMPTS.append(("getaddrinfo", str(args[0]), args[1]))
        elif event == "socket.connect":
            addr = args[1]
            if isinstance(addr, tuple) and len(addr) >= 2:
                _ATTEMPTS.append(("connect", str(addr[0]), addr[1]))
            else:
                _ATTEMPTS.append(("connect", str(addr), None))
    except Exception:
        # An observer must never break the thing it observes.
        _ATTEMPTS.append(("hook-error", event, None))


sys.addaudithook(_audit)


def start_recording() -> int:
    _RECORDING["on"] = True
    return len(_ATTEMPTS)


def take_attempts(mark: int) -> List[Tuple[str, str, Any]]:
    return _ATTEMPTS[mark:]


# Hostnames that must never be contacted. If any appears, the test fails loudly.
FORBIDDEN_HOSTS = (
    "openai.com", "api.openai.com", "openrouter.ai", "anthropic.com", "api.anthropic.com",
    "googleapis.com", "generativelanguage.googleapis.com", "azure.com", "mistral.ai",
    "cohere.ai", "huggingface.co",
)


def check_egress(attempts, endpoint, resolved_ips=()) -> Tuple[bool, str]:
    """Count only the configured host or its observed addresses on the configured port."""
    target = urlsplit(endpoint)
    allowed_hosts = {target.hostname, *resolved_ips}
    target_port = target.port or (443 if target.scheme == "https" else 80)
    bad = []
    for kind, host, port in attempts:
        if kind == "hook-error":
            bad.append(f"audit hook error on {host}")
            continue
        h = host.lower()
        if any(f in h for f in FORBIDDEN_HOSTS):
            bad.append(f"{kind} -> FORBIDDEN {host}:{port}")
            continue
        if h not in allowed_hosts or str(port) != str(target_port):
            bad.append(f"{kind} -> unexpected endpoint {host}:{port}")
    if bad:
        return False, "; ".join(bad[:5])
    hosts = sorted({h for _k, h, _p in attempts})
    return True, f"only {hosts or ['(no network activity)']}"


# ----------------------------------------------------------------------------------
# 2. Static check: no other model endpoint or key anywhere outside docs/.
# ----------------------------------------------------------------------------------
STATIC_PATTERNS = {
    "openai.com": re.compile(rb"openai\.com"),
    "openrouter.ai": re.compile(rb"openrouter\.ai"),
    "anthropic.com": re.compile(rb"anthropic\.com"),
    "api_key=": re.compile(rb"api_key\s*="),
    # Word-bounded so ordinary words ending in "sk-" (risk-, task-) are not false hits.
    "sk-<secret>": re.compile(rb"\bsk-[A-Za-z0-9]{8,}"),
    "OPENAI_": re.compile(rb"OPENAI_"),
}


# Scoped to code and configuration. A second endpoint is only *reachable* if it is in
# something that executes or configures execution; prose that documents this very check
# necessarily names the patterns, and evidence/REPORT.md does. Secrets are a different
# question and are scanned across every file, prose included, before each commit.
CODE_SUFFIXES = {".py", ".json", ".toml", ".cfg", ".ini", ".yaml", ".yml",
                 ".sh", ".ps1", ".js", ".ts", ".tsx", ".jsx", ".env", ".example"}


def static_check() -> Tuple[bool, List[str]]:
    hits: List[str] = []
    skip_dirs = {".git", "docs", "__pycache__", ".venv", "venv", "node_modules", ".clearance"}
    for directory, dirs, files in os.walk(bc.REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for filename in files:
            path = Path(directory) / filename
            if path.suffix not in CODE_SUFFIXES and filename not in (".env", ".env.example"):
                continue
            rel = path.relative_to(bc.REPO_ROOT).as_posix()
            if rel == "scripts/check_failure_test.py":
                continue
            try:
                data = path.read_bytes()
            except OSError:
                hits.append(f"{rel}: could not inspect file")
                continue
            hits.extend(f"{rel}: {name}" for name, pattern in STATIC_PATTERNS.items() if pattern.search(data))
    return (not hits), hits


# ----------------------------------------------------------------------------------
# 3. Local stub endpoints for the 5xx and missing-header scenarios.
# ----------------------------------------------------------------------------------
class _Stub(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.server.mode == "timeout":
            self.server.release.wait()
            return
        if self.server.mode == "503":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            body = b'{"error":{"message":"upstream unavailable","type":"server_error"}}'
        else:
            # HTTP 200 with a perfectly normal completion and NOT ONE X-Brane-* header.
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            body = json.dumps({
                "id": "chatcmpl-stub",
                "model": "stub-model",
                "choices": [{"index": 0, "message": {
                    "role": "assistant",
                    "content": "Outstanding items: commercial invoice DOC-INV-01 and the "
                               "beneficiary's confirmation. Headroom after issue is USD 500,000."
                }}],
            }).encode()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST

    def log_message(self, *a):
        pass


@contextmanager
def local_endpoint(mode):
    if mode == "refused":
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            yield f"http://127.0.0.1:{reserved.getsockname()[1]}/api/v1"
        return
    with HTTPServer(("127.0.0.1", 0), _Stub) as server:
        server.mode = mode
        server.release = threading.Event()
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/api/v1"
        finally:
            server.release.set()
            server.shutdown()
            thread.join()


# ----------------------------------------------------------------------------------
# 4. Scenarios
# ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class Scenario:
    sid: str
    name: str
    definition: str
    timeout: float
    stub: Optional[str] = None
    expect_available: bool = False


def build_scenarios() -> List[Scenario]:
    return [
        Scenario("a", "dns", "BRANE host does not resolve", 10.0),
        Scenario("b", "refused", "connection refused by reserved loopback port", 2.0, stub="refused"),
        Scenario("c", "timeout", "loopback server withholds its response", 0.4, stub="timeout"),
        Scenario("d", "http_5xx", "BRANE returns 503", 10.0, stub="503"),
        Scenario("e", "no_header", "HTTP 200 with a completion and no X-Brane-Routed-To",
                 10.0, stub="200-no-header"),
        Scenario("f", "control", "real BRANE endpoint, healthy", 60.0, expect_available=True),
    ]


def load_client(spec: str) -> Tuple[str, Callable[..., Dict[str, Any]]]:
    """'governed' | 'raw' | 'module:function' (for an external adapter)."""
    if spec == "governed":
        return "scripts/brane_client.py:call_governed", bc.call_governed
    if spec == "raw":
        return "scripts/brane_client.py:call_raw", bc.call_raw
    if ":" not in spec:
        raise SystemExit(f"[refused] --client must be 'governed', 'raw' or 'module:function', got {spec!r}")
    mod_name, func_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    return spec, getattr(mod, func_name)


def run_scenario(sc: Scenario, client: Callable[..., Dict[str, Any]], run_index: int) -> Dict[str, Any]:
    with ExitStack() as scenario:
        if sc.expect_available:
            base_url = bc.base_url()
        else:
            base_url = scenario.enter_context(local_endpoint(sc.stub)) if sc.stub else "https://brane.invalid/api/v1"
            # Faults use a disposable exact URL and dummy credentials, scoped to this call.
            scenario.enter_context(patch.dict(os.environ, {
                "BRANE_BASE_URL": base_url, "BRANE_API_KEY": "synthetic-outage-test",
                "BRANE_TOKEN": "synthetic-outage-test", "no_proxy": "*", "NO_PROXY": "*",
            }))
            scenario.enter_context(patch.object(bc, "ASSIGNED_BASE", base_url))
        mark = start_recording()
        try:
            result = client(PROMPT, timeout=sc.timeout)
        except Exception as exc:
            result = {"outcome": "unavailable", "answer": None, "status": "EXCEPTION",
                      "headers": {}, "reason": type(exc).__name__}
        finally:
            _RECORDING["on"] = False
        attempts = take_attempts(mark)
    egress_ok, egress_note = check_egress(attempts, base_url, SETUP_IPS if sc.expect_available else ())

    outcome = result.get("outcome")
    answer = result.get("answer")
    answer_len = len(answer or "")

    if sc.expect_available:
        connected = any(kind == "connect" for kind, _, _ in attempts)
        ok = outcome in ("direct", "pseudonymized", "local") and answer_len > 0 and connected and egress_ok
        if ok:
            why = f"outcome={outcome}, answer={answer_len} chars, egress {egress_note}"
        elif outcome is None:
            why = ("client performs no outcome classification (adapter contract §3 not "
                   f"implemented); it returned {answer_len} chars, egress {egress_note}")
        else:
            why = f"healthy control: outcome={outcome}, answer={answer_len} chars, connected={connected}, egress {egress_note}"
    else:
        reasons = []
        if outcome is None:
            reasons.append("client performs no outcome classification, so it cannot report "
                           "`unavailable` (adapter contract §3 not implemented)")
        required_event = "getaddrinfo" if sc.sid == "a" else "connect"
        if not any(kind == required_event for kind, _, _ in attempts):
            reasons.append(f"expected {required_event} was not observed")
        expected_status = {"a": "ERROR", "b": "ERROR", "c": "ERROR", "d": "503", "e": "200"}[sc.sid]
        if result.get("status") != expected_status:
            reasons.append(f"expected transport status {expected_status}, observed {result.get('status')}")
        if outcome is not None and outcome != "unavailable":
            reasons.append(f"outcome={outcome!r}, expected 'unavailable'")
        if answer_len:
            reasons.append(f"{answer_len} chars of unverified answer text reached the caller")
        if not egress_ok:
            reasons.append(f"egress violation: {egress_note}")
        ok = not reasons
        why = "; ".join(reasons) if reasons else (
            f"no policy decision, no answer, egress {egress_note}")

    return {
        "scenario": sc.sid, "name": sc.name, "definition": sc.definition,
        "run_index": run_index, "endpoint": base_url, "pinned_host": urlsplit(base_url).hostname,
        "timeout_s": sc.timeout,
        "outcome": outcome, "status": result.get("status"),
        "reason": result.get("reason", ""),
        "answer_chars": answer_len,
        "discarded_answer_chars": result.get("discarded_answer_chars", 0),
        "headers": result.get("headers", {}),
        "egress_attempts": [{"kind": k, "host": h, "port": p} for k, h, p in attempts],
        "egress_hosts": sorted({h for _k, h, _p in attempts}),
        "egress_ok": egress_ok, "egress_note": egress_note,
        "verdict": PASS if ok else FAIL, "verdict_reason": why,
    }


SETUP_IPS: List[str] = []


def resolve_setup_ips() -> None:
    """Resolve the real endpoint once, before recording, so its IPs are known-good."""
    host = bc.ALLOWED_HOST
    SETUP_IPS.clear()
    try:
        for fam, _t, _p, _c, sa in socket.getaddrinfo(host, 443):
            SETUP_IPS.append(sa[0])
    except Exception as exc:
        print(f"[setup] could not pre-resolve {host}: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser(description="A5 / track test 5: protection-check failure.")
    ap.add_argument("--client", default="governed",
                    help="'governed' (default), 'raw', or 'module:function' for an adapter")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", help="comma-separated scenario ids, e.g. a,e")
    ap.add_argument("--output-dir", type=Path, default=bc.REPO_ROOT / "evidence",
                    help="directory for the CSV and raw observations")
    ap.add_argument("--skip-static", action="store_true",
                    help="skip the static endpoint/key check (not for evidence runs)")
    args = ap.parse_args()

    scenarios = build_scenarios()
    if args.runs < 1:
        ap.error("--runs must be positive")
    if args.only is not None:
        want = {sid.strip() for sid in args.only.split(",")}
        if want - {sc.sid for sc in scenarios}:
            ap.error("--only must contain known scenario ids a through f")
        scenarios = [sc for sc in scenarios if sc.sid in want]
    live_control = any(sc.expect_available for sc in scenarios)
    if live_control:
        bc.load_env()
        bc.base_url()
    client_name, client = load_client(args.client)
    print(f"[client] {client_name}")

    print("\n=== Static check: no other model endpoint or key outside docs/ ===")
    if args.skip_static:
        print("  [skipped by flag -- this run is not valid evidence]")
    else:
        ok, hits = static_check()
        for h in hits:
            print(f"  HIT {h}")
        print(f"  {'clean' if ok else str(len(hits)) + ' hit(s)'}")
        if not ok:
            print("\n[ABORT] a second model endpoint or a key is present in the repo. The "
                  "no-fallback property cannot be claimed while that is true.")
            return 2

    if live_control:
        resolve_setup_ips()
        print(f"[setup] real endpoint pre-resolved to {SETUP_IPS or ['(unresolved)']}")

    print(f"\n=== {len(scenarios)} scenarios x {args.runs} run(s) ===")
    records: List[Dict[str, Any]] = []
    for sc in scenarios:
        for i in range(1, args.runs + 1):
            rec = run_scenario(sc, client, i)
            records.append(rec)
            mark = "PASS" if rec["verdict"] == PASS else "FAIL"
            print(f"  [{mark}] {sc.sid} {sc.name:10} run {i}: {rec['verdict_reason'][:120]}")

    stamp = bc.utc_stamp()
    team = (bc.team_build().split("/")[0] or "Redwood").strip()
    csv_path = args.output_dir / f"{team.lower()}-A5-check-failure_{stamp}.csv"
    jsonl_path = args.output_dir / "raw" / f"{team.lower()}-A5-check-failure_{stamp}.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    policy_hash = "offline"
    if live_control:
        status, _h, live, _raw = bc.request("GET", "/policy", timeout=30.0)
        policy_hash = bc.policy_hash(live) if status == "200" and isinstance(live, dict) else "unknown"
    policy_version = f"{team} / A5-check-failure / {policy_hash}"

    with csv_path.open("w", newline="", encoding="utf-8") as cf, \
         jsonl_path.open("w", encoding="utf-8") as jf:
        w = csv.writer(cf)
        w.writerow([
            "Test ID", "Scenario type", "Expected result",
            "Synthetic input (NEVER real personal data)",
            "X-Brane-Routed-To", "X-Brane-Redacted", "X-Brane-Pii-Types / Local-Cause",
            "Agent output & impact on answer usefulness", "Pass/Fail", "Team / Policy version",
        ])
        for rec in records:
            hdrs = rec["headers"]
            w.writerow([
                f"T5c/A5{rec['scenario']}",
                f"Mandatory · Check failure ({rec['name']})",
                "Protection check unavailable: request not sent, no answer returned, zero "
                "egress to any other host",
                f"[{rec['definition']}; endpoint {rec['endpoint']}] {PROMPT}",
                hdrs.get("x-brane-routed-to", f"outcome={rec['outcome']}"),
                hdrs.get("x-brane-redacted", "(no header)"),
                f"egress: {', '.join(rec['egress_hosts']) or 'none'}",
                f"run {rec['run_index']}: {rec['verdict_reason']} || "
                f"answer_chars={rec['answer_chars']} discarded={rec['discarded_answer_chars']} "
                f"|| independent audit-hook observation, not client logging",
                rec["verdict"],
                policy_version,
            ])
            jf.write(json.dumps(bc.scrub({
                "check_id": f"T5c/A5{rec['scenario']}",
                "definition_source": "AI-Z track description §03/§06 'Check failure'; "
                                     "spec §10 E5 renamed A5",
                "client": client_name,
                "timestamp_utc": bc.utc_iso(),
                "policy_version": policy_version, "policy_hash": policy_hash,
                "backend_mode": "live" if rec["scenario"] == "f" else "fault-injected",
                **rec,
            }), ensure_ascii=False) + "\n")

    passed = sum(1 for r in records if r["verdict"] == PASS)
    print(f"\n[total] {passed}/{len(records)} scenario runs passed")
    print(f"[wrote] {bc.rel(csv_path)}")
    print(f"[wrote] {bc.rel(jsonl_path)}")

    by_sc: Dict[str, set] = {}
    for r in records:
        by_sc.setdefault(r["scenario"], set()).add(r["verdict"])
    print("\n=== per scenario (all runs) ===")
    for sid, verdicts in sorted(by_sc.items()):
        v = next(iter(verdicts)) if len(verdicts) == 1 else f"INCONSISTENT {sorted(verdicts)}"
        print(f"  {sid}: {v}")

    all_hosts = sorted({h for r in records for h in r["egress_hosts"]})
    print(f"\n[egress] every host contacted across the whole run: {all_hosts}")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
