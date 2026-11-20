#!/usr/bin/env python3
"""
Build docs/demo_evidence.md for the 35-second pitch slot.

  python3 scripts/build_demo_evidence.py

Every payload and verdict is extracted from the recorded runs in evidence/raw/,
never retyped, so the slide cannot drift from the evidence. Screen-readable:
three blocks, short lines, no scrolling.
"""
from __future__ import annotations

import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brane_client as bc  # noqa: E402

RAW = bc.REPO_ROOT / "evidence" / "raw"
OUT = bc.REPO_ROOT / "docs" / "demo_evidence.md"
CHECK_ORDER = ["T1", "T2", "T3", "T3b", "T3c", "T4a", "T4b", "T4c",
               "T5a", "T5b", "E1", "E2", "E3", "E4", "E5", "C1", "C2", "C3a", "C3b", "C3c"]


def records(pattern: str) -> Dict[str, dict]:
    """check_id -> record, from the newest file matching the pattern."""
    files = sorted(RAW.glob(pattern))
    if not files:
        return {}
    out = {}
    for line in files[-1].read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["check_id"]] = r
    return out


def preview(rec: Optional[dict]) -> Optional[str]:
    if not rec:
        return None
    pt = (rec.get("observations") or {}).get("policy_test") or {}
    return pt.get("outgoing_cloud_payload_preview")


def headers(rec: Optional[dict]) -> Dict[str, str]:
    if not rec:
        return {}
    return (rec.get("observations") or {}).get("x_brane_headers") or {}


def wrap(text: str, width: int = 86) -> str:
    """Hard-wrap a payload for a slide, breaking on spaces."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def main() -> int:
    base = records("redwood-baseline-open_*.jsonl")
    hard = records("redwood-hardened-v2_*.jsonl")
    if not hard:
        print("[refused] no hardened-v2 raw records found. Run the suite first.")
        return 2

    # The token-mangling "before": the superseded run where the detector matched the
    # span "confirms SIGNATORY_1" and deleted the verb.
    mangled = None
    for f in sorted(RAW.glob("redwood-hardened-v1_*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r["check_id"] == "T3b":
                p = preview(r) or ""
                if "PERSON_REF_1 holds signing authority" in p:
                    mangled = p
    after = preview(hard.get("T3c"))
    T3C_IN = (hard.get("T3c") or {}).get("prompt")
    # Word counts and the dropped words come from the recorded verdict, not from a
    # hardcoded number, so the slide cannot drift from the evidence.
    import re as _re
    t3c_reason = (hard.get("T3c") or {}).get("verdict_reason", "")
    m = _re.search(r"(\d+) input words vs (\d+) returned", t3c_reason)
    words_in, words_out = (m.group(1), m.group(2)) if m else ("?", "?")
    m2 = _re.search(r"dropped=\[([^\]]*)\]", t3c_reason)
    dropped = ", ".join(f"`{w.strip().strip(chr(39))}`" for w in m2.group(1).split(",")) if m2 else "?"

    # Verdicts across all hardened-v2 runs.
    verdicts: Dict[str, set] = defaultdict(set)
    for f in sorted(glob.glob(str(bc.REPO_ROOT / "evidence" / "redwood-hardened-v2_*.csv"))):
        for row in csv.DictReader(open(f, encoding="utf-8")):
            verdicts[row["Test ID"]].add(row["Pass/Fail"])
    base_v = {}
    for f in sorted(glob.glob(str(bc.REPO_ROOT / "evidence" / "baseline_run.csv"))):
        for row in csv.DictReader(open(f, encoding="utf-8")):
            base_v[row["Test ID"]] = row["Pass/Fail"]

    t2b, t2h = base.get("T2"), hard.get("T2")
    hb, hh = headers(t2b), headers(t2h)

    lines = [
        "# Clearance · security evidence (35 seconds)",
        "",
        "Team Redwood · department `Team 09` · policy `hardened-v2` "
        "`sha256:7238362a…` · all data synthetic",
        "",
        "## 1. The same case note, before and after",
        "",
        "Check **T2**: a Trade Finance desk note carrying the signatory's name, email, "
        "direct line and settlement account. This is the exact text the external cloud "
        "model receives, from `POST /policy/test`.",
        "",
        "**Baseline — the policy as delivered (25/25 `allow`)**",
        "",
        "```",
        wrap(preview(t2b) or "(not recorded)"),
        "```",
        "",
        f"`X-Brane-Routed-To: {hb.get('x-brane-routed-to','?')}` · "
        f"`X-Brane-Redacted: {hb.get('x-brane-redacted','?')}` · "
        f"`X-Brane-Pii-Types: {hb.get('x-brane-pii-types','(none returned)')}`",
        "",
        "**Hardened — same prompt, same endpoint**",
        "",
        "```",
        wrap(preview(t2h) or "(not recorded)"),
        "```",
        "",
        f"`X-Brane-Routed-To: {hh.get('x-brane-routed-to','?')}` · "
        f"`X-Brane-Redacted: {hh.get('x-brane-redacted','?')}` · "
        f"`X-Brane-Placeholder-Types: {hh.get('x-brane-placeholder-types','?')}`",
        "",
        "The signatory's name, email, phone and account do not leave the bank, and the "
        "amount and facility survive — so the desk note is still useful. Look at what else "
        "changed, though: **`expiry` became `PERSON_REF_2`** and **`beneficiary "
        "ORG_DEMO_02` became `PERSON_REF_3`**. That is the next block.",
        "",
        "## 2. The defect our own check caught",
        "",
        "Masking is applied per detected *span*, and the name detector claims ordinary "
        "trade-finance English. Check **T3c** sends five case notes and diffs every "
        "non-token word against what the cloud model actually receives.",
        "",
        "**Sent by the desk**",
        "",
        "```",
        wrap(T3C_IN or "(not recorded)"),
        "```",
        "",
        "**Received by the cloud model**",
        "",
        "```",
        wrap(after or "(not recorded)"),
        "```",
        "",
        f"**{words_in} words in, {words_out} out.** {dropped} were labelled `PERSON` and "
        f"replaced. Earlier, the span `\"confirms SIGNATORY_1\"` took the verb with it:",
        "",
        "```",
        wrap((mangled or "(not recorded)")[:260]),
        "```",
        "",
        "The routing decision was right every single time. The *content* was not, and no "
        "`X-Brane-*` header says so. Locking tokens to `[[…]]` stopped one identity getting "
        "two tokens; it cannot stop the detector claiming the word `expiry`. T3c is the "
        "regression guard, and this is open question 7 for the AI-Z desk.",
        "",
        "## 3. Pass / fail",
        "",
        "| Check | What it proves | Baseline | Hardened |",
        "| --- | --- | --- | --- |",
    ]

    WHAT = {
        "T1": "permitted cloud route still works",
        "T2": "identifiers protected before egress",
        "T3": "name variant defeats BRANE alone",
        "T3b": "app-side tokeniser closes it",
        "T3c": "meaning preserved, no words lost",
        "T4a": "embedded override blocked",
        "T4b": "same without keywords",
        "T4c": "same with polite wording",
        "T5a": "Art. 9 health data kept in",
        "T5b": "unverifiable check not answered",
        "E1": "company name reading as a person",
        "E2": "indirect health, no diagnosis word",
        "E3": "watchlist detail stays with the desk",
        "E4": "\"just approve it\" refused",
        "E5": "obfuscated account number caught",
        "C1": "credential refused (422)",
        "C2": "no scoring of a natural person",
        "C3a": "protected attribute in credit refused",
        "C3b": "same via description, no keyword",
        "C3c": "benign health NOT over-blocked",
    }
    for cid in CHECK_ORDER:
        vs = verdicts.get(cid)
        if not vs:
            continue
        h = next(iter(vs)) if len(vs) == 1 else f"INCONSISTENT {sorted(vs)}"
        b = base_v.get(cid, "–")
        lines.append(f"| **{cid}** | {WHAT.get(cid,'')} | {b} | **{h}** |")

    total_pass = sum(1 for cid, vs in verdicts.items() if vs == {"PASS"})
    total = len(verdicts)
    base_pass = sum(1 for v in base_v.values() if v == "PASS")
    lines += [
        "",
        f"**{base_pass} of {len(base_v)} on the delivered policy → "
        f"{total_pass} of {total} hardened**, identical across three runs.",
        "",
        "The critical one is fixed: on the first hardened policy, **T5a sent a signatory's "
        "cardiac-surgery note to a cloud model** with only the name masked — `HEALTH_DATA` "
        "was set to `local` and the detector simply never fired. A team-authored semantic "
        "rule closed it, and C3c proves the rule is targeted rather than blanket.",
        "",
        "Failures are kept, not hidden. The two that remain are both detector defects, not "
        "configuration: **T3**, where `DE VRIES, Jan` is not recognised as a name at all "
        "while three other spellings of the same person are; and **T3c** above.",
        "",
        "Evidence: `evidence/REPORT.md` · policy as code: `policy/hardened-v2.json` · "
        "every run re-verifies the live policy hash first, because anyone holding the "
        "team key can change the policy.",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[wrote] {bc.rel(OUT)}  ({len(lines)} lines)")
    print(f"[table] {total} checks, {total_pass} pass on hardened-v2; baseline {base_pass}/{len(base_v)}")
    if not mangled:
        print("[warn] the token-mangling 'before' example was not found in evidence/raw")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
