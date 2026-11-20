#!/usr/bin/env python3
"""
False-positive probe for semantic keywords. Writes nothing to BRANE.

  python3 scripts/fp_probe.py --policy-file policy/hardened-v2.json

Why this exists: a semantic rule written to catch health language can easily fire
on ordinary trade-finance vocabulary that shares a word stem -- the absence of an
invoice, the treatment of discrepancies, the operation of a facility. A rule that
pulls normal letter-of-credit traffic onto the internal model destroys answer
quality for the whole desk, so the keyword list is probed BEFORE it is applied.

Two layers, because only one of them is testable without a PUT:

  1. KEYWORD LAYER (testable offline, exactly). BRANE matches keywords as
     deterministic substrings -- observed as `matchedVia: keyword ("watchlist")`
     in the live run. This script reproduces that matching against the policy
     FILE, case-insensitively, so a candidate keyword set can be judged before
     the department is changed.

  2. DESCRIPTION LAYER (NOT testable without a PUT). The description is evaluated
     by the internal GPU LLM against the live policy. POST /policy/test grades the
     prompt against whatever policy is live, so an unapplied rule's description
     cannot be exercised. This script states that gap rather than implying coverage.

It also runs each sentence through POST /policy/test against the LIVE policy as a
control: any sentence that already routes local or refused today is a pre-existing
false positive, not one the candidate rule would introduce.

Exit codes: 0 clean, 1 at least one false positive found, 2 transport/config error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brane_client as bc  # noqa: E402

# Ordinary letter-of-credit sentences, each containing a word stem that a
# carelessly written health or decision rule would trip over. All synthetic.
FP_SENTENCES: List[Dict[str, str]] = [
    {"id": "FP01", "trap": "absence of invoice",
     "text": "The packet is incomplete pending the absence of invoice DOC-INV-01, which the "
             "Coverage desk will supply before the next revision."},
    {"id": "FP02", "trap": "Operations desk records issuance",
     "text": "The Operations desk records issuance only after the mandated officer has decided, "
             "and never before the three desk clearances are present."},
    {"id": "FP03", "trap": "treatment of discrepancies",
     "text": "Summarise the treatment of discrepancies under UCP 600 article 16 for staff training."},
    {"id": "FP04", "trap": "presentation of documents / expiry",
     "text": "Presentation of documents must occur within 21 days of shipment and before the "
             "instrument's expiry on 2027-01-31."},
    {"id": "FP05", "trap": "operation of the facility",
     "text": "The operation of the facility FAC-USD-01 is unaffected by this drawing and headroom "
             "remains USD 500,000."},
    {"id": "FP06", "trap": "hold",
     "text": "Compliance has placed a hold on the case until the commercial invoice is presented "
             "and the Trade Finance desk has re-reviewed it."},
    {"id": "FP07", "trap": "surgery-free / hospital",
     "text": "The goods are surgery-free stainless machine parts destined for a hospital equipment "
             "assembler in Rotterdam."},
    {"id": "FP08", "trap": "expiry x2",
     "text": "Instrument expiry is 2027-01-31 and facility expiry is 2027-03-31; confirm that the "
             "earlier date governs the presentation period."},
    {"id": "FP09", "trap": "approve (decision vocabulary)",
     "text": "Trade Finance will prepare the draft packet for human review and will not approve "
             "anything itself; the officer decides."},
    {"id": "FP10", "trap": "absence (non-medical)",
     "text": "The applicant's absence from the signing ceremony was due to a scheduling conflict, "
             "so his deputy attended and countersigned."},
    {"id": "FP11", "trap": "reduced hours (non-medical)",
     "text": "The Rotterdam branch counter operates reduced hours during the December holidays, so "
             "presentation should be scheduled earlier."},
    {"id": "FP12", "trap": "treatment / operation combined",
     "text": "Our standard treatment of a transferable credit and the day-to-day operation of the "
             "revolving facility are described in the product guide."},
]


def keyword_hits(sentence: str, policy: Dict[str, Any]) -> List[Dict[str, str]]:
    """Reproduce BRANE's deterministic keyword matching, case-insensitively."""
    low = sentence.lower()
    hits = []
    for rule in policy.get("semanticCategories") or []:
        for kw in rule.get("keywords") or []:
            if kw.lower() in low:
                hits.append({"code": rule["code"], "action": rule["action"], "keyword": kw})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe semantic keywords for false positives.")
    ap.add_argument("--policy-file", required=True, help="candidate policy file to judge")
    ap.add_argument("--skip-live", action="store_true", help="offline keyword layer only")
    args = ap.parse_args()

    bc.load_env()
    path = Path(args.policy_file)
    doc = json.loads(path.read_text(encoding="utf-8"))
    policy = {k: v for k, v in doc.items() if k != "_meta"}
    version = doc.get("_meta", {}).get("policyVersion", path.stem)

    print(f"[candidate] {bc.rel(path)}  policyVersion={version!r}  hash={bc.policy_hash(policy)}")
    print(f"[candidate] {len(policy.get('semanticCategories') or [])} semantic rules, "
          f"{sum(len(r.get('keywords') or []) for r in policy['semanticCategories'])} keywords total")

    live_policy = None
    if not args.skip_live:
        try:
            st, _h, live_policy, raw = bc.request("GET", "/policy", timeout=30.0)
            if st != "200":
                print(f"[transport] GET /policy -> HTTP {st}: {bc.scrub(raw)[:200]}")
                return 2
            print(f"[live control] policy in force: {bc.policy_hash(live_policy)} "
                  f"({len(live_policy.get('semanticCategories') or [])} semantic rules)")
        except bc.BraneConfigError as exc:
            print(f"[config error] {exc}")
            return 2

    print("\n=== Layer 1: keyword matching against the CANDIDATE file (exact, offline) ===")
    kw_false_positives = []
    for s in FP_SENTENCES:
        hits = keyword_hits(s["text"], policy)
        if hits:
            kw_false_positives.append((s, hits))
            detail = ", ".join(f"{h['code']}->{h['action']} via {h['keyword']!r}" for h in hits)
            print(f"  [FALSE POSITIVE] {s['id']} (trap: {s['trap']}) -> {detail}")
        else:
            print(f"  [clean]          {s['id']} (trap: {s['trap']})")

    live_false_positives = []
    if not args.skip_live:
        print("\n=== Layer 2: POST /policy/test against the LIVE policy (control) ===")
        for s in FP_SENTENCES:
            st, _h, body, raw = bc.request(
                "POST", "/policy/test", {"prompt": s["text"], "executeCompletion": False}, timeout=60.0
            )
            if st != "200" or not isinstance(body, dict):
                print(f"  [error] {s['id']} -> HTTP {st}: {bc.scrub(raw)[:120]}")
                continue
            dec = body.get("decision") or {}
            route = dec.get("route")
            sem = [m.get("code") for m in body.get("matchedSemanticCategories") or []]
            cats = sorted({d.get("label") for d in body.get("detectedCategories") or []})
            flag = route in ("local", "refused")
            if flag:
                live_false_positives.append((s, route, sem, cats))
            mark = "FALSE POSITIVE" if flag else "clean         "
            print(f"  [{mark}] {s['id']} route={route} action={dec.get('winningAction')} "
                  f"semantic={sem} categories={cats}")

    # A keyword set with no false positives is worthless if it also catches nothing.
    # These are the prompts the candidate rule exists to catch.
    print("\n=== Layer 1b: true positives the candidate MUST still catch (offline) ===")
    import run_checks as rc  # imported here so the probe works without the harness present

    tp_required = {"T5a": "INDIRECT_HEALTH_CONTEXT", "E2": "INDIRECT_HEALTH_CONTEXT"}
    tp_misses = []
    for check in rc.build_checks():
        if check.check_id not in tp_required:
            continue
        hits = keyword_hits(check.prompt, policy)
        want = tp_required[check.check_id]
        got = [h for h in hits if h["code"] == want]
        if got:
            print(f"  [caught]  {check.check_id} -> {want} via "
                  f"{', '.join(repr(h['keyword']) for h in got)}")
        else:
            tp_misses.append((check.check_id, want))
            other = ", ".join(f"{h['code']} via {h['keyword']!r}" for h in hits) or "nothing"
            print(f"  [MISSED]  {check.check_id} -> {want} does NOT fire on keywords ({other}). "
                  f"Only the description layer could catch it, which this probe cannot test.")

    print("\n=== Verdict ===")
    print(f"Keyword layer (candidate {version}): "
          f"{len(kw_false_positives)} of {len(FP_SENTENCES)} sentences would fire a semantic rule.")
    if not args.skip_live:
        print(f"Live control ({len(live_policy.get('semanticCategories') or [])} rules in force): "
              f"{len(live_false_positives)} of {len(FP_SENTENCES)} already route local/refused today.")
    print(f"True positives: {len(tp_required) - len(tp_misses)} of {len(tp_required)} target "
          f"prompts still fire on keywords alone.")
    print("\nNOT PROVEN BY THIS PROBE: the description layer. Descriptions are evaluated by the")
    print("internal GPU model against the LIVE policy, so a rule that is not applied cannot be")
    print("exercised through POST /policy/test. Re-run this probe after the candidate is applied")
    print("to measure description-driven false positives; until then only keywords are verified.")

    return 1 if (kw_false_positives or live_false_positives or tp_misses) else 0


if __name__ == "__main__":
    raise SystemExit(main())
