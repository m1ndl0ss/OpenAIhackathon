#!/usr/bin/env python3
"""Snapshot, compare or apply a versioned BRANE policy.

Writes require --yes. After applying a policy the tool reads the department
configuration back and compares its authored fields with the selected file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brane_client as bc  # noqa: E402

# Keys inside a policy file that are ours, not BRANE's. Stripped before PUT.
META_KEY = "_meta"


def load_policy_file(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (writable_policy, meta). Fails loudly on anything unexpected."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    meta = doc.get(META_KEY, {})
    policy = {k: v for k, v in doc.items() if k != META_KEY}

    unknown = [k for k in policy if k not in bc.WRITABLE_POLICY_FIELDS]
    if unknown:
        raise SystemExit(
            f"[refused] {path} contains fields PUT /policy does not accept: {unknown}. "
            f"Accepted: {list(bc.WRITABLE_POLICY_FIELDS)}"
        )
    return policy, meta


def get_live() -> Dict[str, Any]:
    status, _headers, body, raw = bc.request("GET", "/policy", timeout=30.0)
    if status != "200" or not isinstance(body, dict):
        raise SystemExit(f"[transport] GET /policy -> HTTP {status}: {bc.scrub(raw)[:300]}")
    return body


def semantic_by_code(policy: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for entry in policy.get("semanticCategories") or []:
        if isinstance(entry, dict) and entry.get("code"):
            out[str(entry["code"])] = entry
    return out


def diff_policy(want: Dict[str, Any], live: Dict[str, Any]) -> List[str]:
    """
    Human-readable differences between the file (want) and the live policy.
    Empty list means the live policy already matches the file exactly.

    Extra fields BRANE adds to a semantic rule (ids, timestamps) are not
    treated as drift; a field we sent coming back changed or missing is.
    """
    diffs: List[str] = []

    for field in ("routingMode", "piiSensitivity"):
        if field in want and want[field] != live.get(field):
            diffs.append(f"{field}: live={live.get(field)!r} -> file={want[field]!r}")

    want_cats = want.get("categories") or {}
    live_cats = live.get("categories") or {}
    for label in sorted(set(want_cats) | set(live_cats)):
        w, l = want_cats.get(label), live_cats.get(label)
        if label not in want_cats:
            diffs.append(f"categories.{label}: live={l!r} -> (absent from file)")
        elif w != l:
            diffs.append(f"categories.{label}: live={l!r} -> file={w!r}")

    want_sem, live_sem = semantic_by_code(want), semantic_by_code(live)
    for code in sorted(set(want_sem) | set(live_sem)):
        if code not in want_sem:
            diffs.append(f"semanticCategories.{code}: live has it -> (absent from file)")
        elif code not in live_sem:
            diffs.append(f"semanticCategories.{code}: (not live) -> file adds it "
                         f"(action={want_sem[code].get('action')!r})")
        else:
            for key, wv in want_sem[code].items():
                lv = live_sem[code].get(key)
                if wv != lv:
                    diffs.append(f"semanticCategories.{code}.{key}: live={lv!r} -> file={wv!r}")
            # BRANE adds `enabled` on storage. A stored-but-disabled rule enforces
            # nothing, so it is drift even though we never send the field.
            if live_sem[code].get("enabled") is False:
                diffs.append(f"semanticCategories.{code}.enabled: live=False -> rule is stored "
                             f"but INERT; it enforces nothing")
    return diffs


def print_diff(diffs: List[str], want: Dict[str, Any], live: Dict[str, Any]) -> None:
    print(f"\n[live]   hash={bc.policy_hash(live)}  "
          f"summary={json.dumps(live.get('summary', {}), separators=(',', ':'))}")
    print(f"[file]   hash={bc.policy_hash(want)}")
    if not diffs:
        print("\n[diff] none — the live policy already matches the file.")
        return
    print(f"\n[diff] {len(diffs)} change(s) the file would make:")
    for line in diffs:
        print(f"    {line}")


def verify_applied(want: Dict[str, Any]) -> int:
    """GET and prove the live policy equals the file. Returns an exit code."""
    live = get_live()
    diffs = diff_policy(want, live)
    if diffs:
        print(f"\n[FAIL] read-back does not match the file ({len(diffs)} mismatch(es)):")
        for line in diffs:
            print(f"    {line}")
        print("[FAIL] the department is NOT in the intended state. Do not run evidence against it.")
        return 1
    print(f"\n[verified] read-back matches the file exactly.  policy_hash={bc.policy_hash(live)}")
    s = live.get("summary", {})
    print(f"[verified] summary: allow={s.get('allow')} placeholder={s.get('placeholder')} "
          f"local={s.get('local')} refuse={s.get('refuse')} "
          f"semantic={s.get('activeSemanticCategories')} openBaseline={s.get('isOpenBaseline')}")
    return 0


def put_policy(policy: Dict[str, Any]) -> Dict[str, str]:
    status, headers, body, raw = bc.request("PUT", "/policy", policy, timeout=30.0)
    print(f"[PUT /policy] HTTP {status}")
    if status != "200":
        raise SystemExit(f"[transport] PUT /policy -> HTTP {status}: {bc.scrub(raw)[:400]}")
    if isinstance(body, dict):
        s = body.get("summary", {})
        print(f"[PUT response] summary: allow={s.get('allow')} placeholder={s.get('placeholder')} "
              f"local={s.get('local')} refuse={s.get('refuse')} "
              f"semantic={s.get('activeSemanticCategories')}")
    return headers


def mode_snapshot(path: Path) -> int:
    live = get_live()
    doc = bc.writable_policy(live)
    doc[META_KEY] = {
        "capturedUtc": bc.utc_iso(),
        "source": "GET /policy (live, unmodified)",
        "team": live.get("team"),
        "departmentId": live.get("departmentId"),
        "policyHash": bc.policy_hash(live),
        "summaryAtCapture": live.get("summary"),
        "note": "Writable fields only, so this file can be PUT back verbatim to restore.",
    }
    bc.write_json(path, doc)
    print(f"[snapshot] wrote {bc.rel(path)}  hash={bc.policy_hash(live)}")
    print(f"[snapshot] team={live.get('team')!r} isOpenBaseline={live.get('summary', {}).get('isOpenBaseline')}")
    return 0


def mode_diff(path: Path) -> int:
    want, meta = load_policy_file(path)
    if meta.get("policyVersion"):
        print(f"[file] {path.name}  policyVersion={meta['policyVersion']!r}")
    print_diff(diff_policy(want, get_live()), want, get_live())
    return 0


def mode_apply(path: Path, confirmed: bool) -> int:
    want, meta = load_policy_file(path)
    live = get_live()
    diffs = diff_policy(want, live)
    version = meta.get("policyVersion", path.stem)
    print(f"[file] {path.name}  policyVersion={version!r}")
    print_diff(diffs, want, live)

    if not confirmed:
        print("\n[refused] --yes not given, so nothing was written. This was a dry run.")
        return 3
    if not diffs:
        print("\n[idempotent] live policy already matches; PUT skipped, verifying anyway.")
        return verify_applied(want)

    print(f"\n[applying] PUT {len(diffs)} change(s)...")
    put_policy(want)
    return verify_applied(want)


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply, diff or snapshot the BRANE policy.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", metavar="PATH", help="read-only: save live policy to PATH")
    g.add_argument("--diff", metavar="PATH", help="read-only: diff PATH against live policy")
    g.add_argument("--apply", metavar="PATH", help="PUT PATH, then read back and verify")
    ap.add_argument("--yes", action="store_true", help="required for anything that writes")
    args = ap.parse_args()

    bc.load_env()
    try:
        print(f"[config] base_url={bc.base_url()}  key {bc.key_fingerprint()}")
    except bc.BraneConfigError as exc:
        print(f"[config error] {exc}")
        return 2

    if args.snapshot:
        return mode_snapshot(Path(args.snapshot))
    if args.diff:
        return mode_diff(Path(args.diff))
    return mode_apply(Path(args.apply), args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
