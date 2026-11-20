#!/usr/bin/env python3
"""
App-side case tokeniser: defence in depth in front of BRANE.

  python3 scripts/case_tokeniser.py --self-test
  python3 scripts/case_tokeniser.py --text "Mandate shows DE VRIES, Jan ..."

Why this exists. On hardened-v1, BRANE pseudonymised four of five forms of one
signatory's identity but missed the surname-first form `DE VRIES, Jan`, which
reached the cloud model verbatim (T3 FAIL). It also assigns tokens per surface
form rather than per identity, so `Jan de Vries` and `J. de Vries` became
PERSON_REF_1 and PERSON_REF_2 -- two tokens for one person, which breaks exactly
the identity-reconciliation task the desk needs.

This module fixes both app-side, BEFORE the BRANE call, because the bank knows
who the case parties are and does not have to infer them:

  * every known alias of a party maps to ONE case-scoped token (SIGNATORY_1,
    ORG_DEMO_01), so identity consistency survives;
  * aliases include the forms the detector missed -- surname-first, initials,
    uppercase, comma-separated;
  * the alias -> token mapping is written to a local, git-ignored file. It is the
    rehydration key and is treated as sensitive: it stays out of git, out of the
    model payload and out of the committed evidence.

BRANE remains the enforcement boundary. This narrows what reaches it; it does not
replace it. Anything the bank does not know about is still BRANE's job.

Replacement order is longest-alias-first, so "Jan de Vries" is consumed before
"Jan" and no token is built out of a partial match.

Token SHAPES matter and were chosen empirically, not by taste. Word-like compound
tokens get read as names by BRANE's NER and are then re-tokenised in SOME positions
only, which splits one identifier across two surfaces and re-introduces exactly the
inconsistency this module removes. Measured on the T3b prompt, 4 identical calls each:

    SIGNATORY_1_ACCOUNT   1 of 3 occurrences survived  (labelled PERSON)
    CASE_ACCOUNT_A        2 of 3 occurrences survived  (labelled PERSON)
    [[ACCT-A]]            3 of 3, stable
    #ACCT-A#              3 of 3, stable
    acct-ref-a            3 of 3, stable

The outcome is context-sensitive rather than random: the same token survived
differently when a neighbouring token changed, and each shape was stable across
repeats. A word-like person token failed the same way once the identifier tokens
were fixed -- the NER matched the span 'confirms SIGNATORY_1', swallowing the verb
as part of the name and corrupting the sentence as well as splitting the identity.
Every party token is therefore bracketed. ORG_DEMO_01/02 keep the fixture's own
identifiers, which BRANE labels ORG and tokenises uniformly.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brane_client as bc  # noqa: E402

# Local, git-ignored. Holds the rehydration key for the demo case.
MAP_PATH = bc.REPO_ROOT / "local" / "case_alias_map.json"

# --------------------------------------------------------------------------------------
# Case parties for fixture LC-DEMO-001. All synthetic.
# Aliases deliberately include the forms BRANE's detector missed.
# --------------------------------------------------------------------------------------
CASE_PARTIES: Dict[str, Dict[str, object]] = {
    "[[SIGNATORY-1]]": {
        "role": "Authorised signatory of ORG_DEMO_01 (natural person, synthetic)",
        "aliases": [
            "Jan de Vries",
            "Jan De Vries",
            "JAN DE VRIES",
            "DE VRIES, Jan",
            "DE VRIES, JAN",
            "de Vries, Jan",
            "J. de Vries",
            "J. De Vries",
            "J. DE VRIES",
            "J de Vries",
            "de Vries",
        ],
    },
    "[[EMAIL-A]]": {
        "role": "Signatory's work email (synthetic, .example domain)",
        "aliases": [
            "jan.de.vries@orgdemo01.example",
            "JAN.DE.VRIES@ORGDEMO01.EXAMPLE",
        ],
    },
    "[[ACCT-A]]": {
        "role": "Settlement account of the signatory (synthetic, non-issued)",
        "aliases": [
            "NL02ABNA0123456789",
            "NL02 ABNA 0123 4567 89",
            "NL02.ABNA.0123.456789",
        ],
    },
    "[[PHONE-A]]": {
        "role": "Signatory's direct line (synthetic, 555 range)",
        "aliases": ["+31 20 5550147", "+31205550147", "0031 20 5550147"],
    },
    "ORG_DEMO_01": {
        "role": "Applicant, Dutch importer (synthetic)",
        "aliases": [
            "Van der Meer Machinery B.V.",
            "Van der Meer Machinery BV",
            "Van der Meer Machinery",
            "Jansen & De Vries Machinery B.V.",
            "Jansen & De Vries Machinery BV",
            "Jansen & De Vries Machinery",
        ],
    },
    "ORG_DEMO_02": {
        "role": "Beneficiary, US supplier (synthetic)",
        "aliases": [
            "Lakeside Components Inc.",
            "Lakeside Components Inc",
            "Lakeside Components",
        ],
    },
}


def all_aliases() -> List[Tuple[str, str]]:
    """(alias, token) pairs, longest alias first so partial matches cannot win."""
    pairs = [
        (alias, token)
        for token, party in CASE_PARTIES.items()
        for alias in party["aliases"]  # type: ignore[index]
    ]
    return sorted(pairs, key=lambda p: len(p[0]), reverse=True)


def write_map() -> Path:
    """Persist the rehydration key locally. Idempotent."""
    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "_warning": "LOCAL ONLY. Rehydration key for synthetic case LC-DEMO-001. "
                    "Git-ignored. Never send to a model, never commit, never attach to evidence.",
        "fixture_id": "LC-DEMO-001",
        "generatedUtc": bc.utc_iso(),
        "parties": CASE_PARTIES,
    }
    MAP_PATH.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return MAP_PATH


def tokenise(text: str) -> Tuple[str, Dict[str, object]]:
    """
    Replace every known alias with its case-scoped token.

    Returns (tokenised_text, report) where report records, per token, which
    aliases were found and how many times -- the evidence that all variants of
    one identity collapsed to a single token.
    """
    out = text
    found: Dict[str, Dict[str, int]] = {}
    for alias, token in all_aliases():
        # Case-sensitive on purpose: each casing variant is listed explicitly, so a
        # match is always a known form rather than a loose guess.
        count = out.count(alias)
        if count:
            out = out.replace(alias, token)
            found.setdefault(token, {})[alias] = count

    report = {
        "tokens_applied": {t: sum(a.values()) for t, a in found.items()},
        "aliases_matched": found,
        "total_replacements": sum(sum(a.values()) for a in found.values()),
    }
    return out, report


def rehydrate(text: str) -> str:
    """Restore the canonical alias for each token. For bank-side display only."""
    out = text
    for token, party in CASE_PARTIES.items():
        canonical = party["aliases"][0]  # type: ignore[index]
        out = out.replace(token, canonical)
    return out


def surviving_aliases(text: str) -> List[str]:
    """Any known alias still present. Must be empty after tokenise()."""
    return sorted({alias for alias, _token in all_aliases() if alias in text})


# [[...]] is the ONLY permitted token shape. Word-like tokens were measured to be
# re-detected by BRANE's NER in some positions and not others, which splits one
# identity across two surfaces and once deleted an adjacent verb. Do not add a token
# in any other shape, and do not accept one in a model reply.
TOKEN_SHAPE = re.compile(r"\[\[[A-Za-z0-9_\-]+\]\]")


def validate_reply_tokens(reply: str) -> Tuple[bool, Dict[str, object]]:
    """
    Output-validator rule for the rehydration round trip.

    Every [[token]] in a model reply must be one this case issued. A token that is
    unknown, mangled, or invented means the reply cannot be safely rehydrated: at
    best a placeholder is shown to a reviewer as if it were a fact, at worst the
    wrong party's identity is substituted into a desk packet.

    Returns (ok, report). ok=False means REJECT the output -- do not rehydrate, do
    not seal a packet, request a bounded correction or escalate.
    """
    known = set(CASE_PARTIES)
    found = TOKEN_SHAPE.findall(reply)
    unknown = sorted({t for t in found if t not in known})

    # Bracket-ish fragments that did not parse as a well-formed token at all:
    # "[[SIGNATORY-1", "[[PERSON_REF_1]]" wrapped twice, truncated spans, and so on.
    bracket_fragments = re.findall(r"\[\[[^\]]{0,40}(?:\]\]|$)", reply)
    malformed = sorted({f for f in bracket_fragments if not TOKEN_SHAPE.fullmatch(f)})

    report = {
        "tokens_found": sorted(set(found)),
        "unknown_tokens": unknown,
        "malformed_token_spans": malformed,
        "known_tokens_for_case": sorted(known),
    }
    return (not unknown and not malformed), report


def self_test() -> int:
    """Checks the T3 failure mode specifically, offline."""
    sample = (
        "Mandate reconciliation for LC-001. (1) Jan de Vries is listed as first signatory, "
        "contact jan.de.vries@orgdemo01.example, settlement NL02ABNA0123456789. "
        "(2) The mandate register shows DE VRIES, Jan with account NL02ABNA0123456789. "
        "(3) The board minute refers to J. de Vries only. (4) Correspondence from "
        "jan.de.vries@orgdemo01.example confirms Jan de Vries holds signing authority."
    )
    out, report = tokenise(sample)
    leaks = surviving_aliases(out)
    name_token_count = out.count("[[SIGNATORY-1]]")

    print("--- input ---")
    print(sample)
    print("\n--- tokenised ---")
    print(out)
    print("\n--- report ---")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    ok = True
    if leaks:
        print(f"\n[FAIL] aliases survived tokenisation: {leaks}")
        ok = False
    else:
        print("\n[ok] no known alias survived")

    if name_token_count != 4:
        print(f"[FAIL] expected 4 occurrences of [[SIGNATORY-1]] (3 name forms + 1 repeat), "
              f"got {name_token_count}")
        ok = False
    else:
        print("[ok] all three name forms (full, surname-first, initial) collapsed to "
              "[[SIGNATORY-1]], 4 occurrences")

    if "DE VRIES, Jan" in out:
        print("[FAIL] the surname-first form BRANE missed is still present")
        ok = False
    else:
        print("[ok] surname-first form 'DE VRIES, Jan' replaced (this is the T3 leak)")

    restored = rehydrate(out)
    if "Jan de Vries" not in restored:
        print("[FAIL] rehydration did not restore the canonical name")
        ok = False
    else:
        print("[ok] rehydration restores the canonical name bank-side")

    path = write_map()
    print(f"[ok] rehydration key written to {bc.rel(path)} (git-ignored)")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Tokenise case-party aliases before the BRANE call.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true")
    g.add_argument("--text", help="text to tokenise")
    g.add_argument("--write-map", action="store_true", help="write the local rehydration key")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.write_map:
        print(f"[wrote] {bc.rel(write_map())}")
        return 0
    out, report = tokenise(args.text)
    print(out)
    print(json.dumps(report, indent=2, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
