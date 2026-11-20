#!/usr/bin/env python3
"""Compare the deployed BRANE policy with the committed definition.

Reads the department policy and checks its digest and enabled semantic rules.
The default reference is hardened-v2. Exit codes are 0 for a match, 1 for drift
and 2 for a configuration or transport error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brane_client as bc  # noqa: E402

DEFAULT_POLICY = "policy/hardened-v2.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the live BRANE policy against a committed file.")
    ap.add_argument("--policy-file", default=DEFAULT_POLICY,
                    help=f"committed policy to verify against (default {DEFAULT_POLICY})")
    ap.add_argument("--expect-hash", help="additionally require this exact canonical hash")
    ap.add_argument("--quiet", action="store_true", help="only print the verdict line")
    args = ap.parse_args()

    bc.load_env()
    try:
        base = bc.base_url()
    except bc.BraneConfigError as exc:
        print(f"[config error] {exc}")
        return 2

    path = Path(args.policy_file)
    if not path.exists():
        print(f"[config error] {bc.rel(path)} does not exist")
        return 2
    doc = json.loads(path.read_text(encoding="utf-8"))
    want = {k: v for k, v in doc.items() if k != "_meta"}
    want_hash = bc.policy_hash(want)
    version = doc.get("_meta", {}).get("policyVersion", path.stem)

    status, _headers, live, raw = bc.request("GET", "/policy", timeout=30.0)
    if status != "200" or not isinstance(live, dict):
        print(f"[transport] GET /policy -> HTTP {status}: {bc.scrub(raw)[:300]}")
        return 2
    live_hash = bc.policy_hash(live)

    if not args.quiet:
        s = live.get("summary", {})
        print(f"[endpoint] {base}")
        print(f"[file]     {bc.rel(path)}  policyVersion={version!r}  hash={want_hash}")
        print(f"[live]     team={live.get('team')!r}  hash={live_hash}")
        print(f"[live]     routingMode={live.get('routingMode')} "
              f"piiSensitivity={live.get('piiSensitivity')} allow={s.get('allow')} "
              f"placeholder={s.get('placeholder')} local={s.get('local')} refuse={s.get('refuse')} "
              f"semantic={s.get('activeSemanticCategories')}")

    if live_hash != want_hash:
        print(f"\n[DRIFT] the live policy is NOT {version}.")
        print(f"        live = {live_hash}")
        print(f"        file = {want_hash}")
        print("        Anyone with the team key can change the department, including through the")
        print("        /team-policy web workbench. Do not file evidence against this state.")
        print(f"        Fix: python3 scripts/apply_policy.py --apply {bc.rel(path)} --yes")
        return 1

    if args.expect_hash and live_hash != args.expect_hash:
        print(f"\n[DRIFT] live hash {live_hash} does not equal --expect-hash {args.expect_hash}")
        return 1

    # A rule can be stored but disabled, which hashes the same as authored but
    # enforces nothing. Check it explicitly.
    inert = [r.get("code") for r in live.get("semanticCategories") or []
             if isinstance(r, dict) and r.get("enabled") is False]
    if inert:
        print(f"\n[DRIFT] semantic rules are stored but DISABLED and enforce nothing: {inert}")
        return 1

    print(f"\n[VERIFIED] live policy == {version} ({live_hash}), "
          f"{len(live.get('semanticCategories') or [])} semantic rules all enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
