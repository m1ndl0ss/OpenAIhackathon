#!/usr/bin/env python3
"""
Read-only BRANE discovery for team Redwood. Writes nothing to BRANE.

  python3 scripts/discover.py

Saves (key scrubbed, idempotent — same files overwritten each run):
  policy/discovery/models.json          GET /models
  policy/discovery/policy_catalog.json  GET /policy/catalog
  policy/discovery/policy_current.json  GET /policy
  policy/discovery/shape_notes.json     machine-readable summary of what we observed

Then prints the policy object's exact JSON shape and the category codes, so the
hardened policy can be written against what the endpoint actually returns
instead of against the README.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brane_client as bc  # noqa: E402

DISCOVERY_DIR = bc.REPO_ROOT / "policy" / "discovery"


def describe_shape(value, depth: int = 0, max_depth: int = 3):
    """Type skeleton of a JSON value: keys and value types, not the values."""
    if depth >= max_depth:
        return type(value).__name__
    if isinstance(value, dict):
        return {k: describe_shape(v, depth + 1, max_depth) for k, v in value.items()}
    if isinstance(value, list):
        if not value:
            return "list[empty]"
        return [describe_shape(value[0], depth + 1, max_depth), f"...x{len(value)}"]
    if value is None:
        return "null"
    return type(value).__name__


def fetch(label: str, path: str, filename: str, auth: bool = True) -> dict:
    status, headers, parsed, raw = bc.request("GET", path, auth=auth, timeout=30.0)
    record = {
        "endpoint": path,
        "method": "GET",
        "http_status": status,
        "authenticated": auth,
        "retrieved_utc": bc.utc_iso(),
        "brane_headers": bc.brane_headers(headers),
        "body": parsed if parsed is not None else bc.scrub(raw),
    }
    bc.write_json(DISCOVERY_DIR / filename, record)
    marker = "ok" if status.startswith("2") else "PROBLEM"
    print(f"[{marker}] GET {path} -> HTTP {status}  saved policy/discovery/{filename}")
    if not status.startswith("2"):
        print(f"       body: {bc.scrub(raw)[:300]}")
    return record


def main() -> int:
    bc.load_env()
    try:
        print(f"[config] base_url={bc.base_url()}  key {bc.key_fingerprint()}  team_build={bc.team_build()!r}")
    except bc.BraneConfigError as exc:
        print(f"[config error] {exc}")
        return 2

    models = fetch("models", "/models", "models.json", auth=True)
    catalog = fetch("catalog", "/policy/catalog", "policy_catalog.json", auth=False)
    current = fetch("policy", "/policy", "policy_current.json", auth=True)

    failures = [r["endpoint"] for r in (models, catalog, current) if not str(r["http_status"]).startswith("2")]

    notes = {
        "retrieved_utc": bc.utc_iso(),
        "base_url": bc.base_url(),
        "endpoints": {
            r["endpoint"]: {"http_status": r["http_status"], "authenticated": r["authenticated"]}
            for r in (models, catalog, current)
        },
        "models_shape": describe_shape(models["body"]),
        "catalog_shape": describe_shape(catalog["body"]),
        "policy_shape": describe_shape(current["body"]),
    }
    bc.write_json(DISCOVERY_DIR / "shape_notes.json", notes)

    print("\n=== GET /policy shape (top level) ===")
    body = current["body"]
    if isinstance(body, dict):
        for k, v in body.items():
            print(f"  {k}: {describe_shape(v, 1, 3)}")
    else:
        print(f"  (not an object) {describe_shape(body)}")

    print("\n=== GET /policy/catalog ===")
    cat = catalog["body"]
    if isinstance(cat, dict):
        for k, v in cat.items():
            print(f"  {k}: {describe_shape(v, 1, 2)}")
        cats = cat.get("categories")
        if isinstance(cats, list):
            print(f"\n  {len(cats)} categories:")
            for entry in cats:
                if isinstance(entry, dict):
                    code = entry.get("code") or entry.get("id") or entry.get("label")
                    group = entry.get("group", "?")
                    actions = entry.get("allowedActions") or entry.get("actions") or ""
                    locked = entry.get("locked", entry.get("securityFloor", ""))
                    print(f"    {str(code):22} group={str(group):14} actions={actions} floor/locked={locked}")
                else:
                    print(f"    {entry}")

    print("\n=== GET /models ===")
    mb = models["body"]
    if isinstance(mb, dict) and isinstance(mb.get("data"), list):
        for m in mb["data"]:
            if isinstance(m, dict):
                print(f"    {m.get('id')}  owned_by={m.get('owned_by', '?')}")
    print("\n[next] Shape confirmed from the live endpoint. PUT semantics (full replace vs")
    print("       partial merge) are verified separately in scripts/probe_put_semantics.py,")
    print("       which needs explicit approval because it writes.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
