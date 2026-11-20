"""Run the two clean LC scenarios from Ilaria's case worksheet and export utility evidence."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from backend.integrations import prepare_packets
from backend.store import identifier, snapshot

# Expected values are transcribed from legal/case-answer-key.md, independent of the agent calculation.
EXPECTATIONS = {
    1: {"headroom_before_minor": 250_000_000, "headroom_after_minor": 50_000_000,
        "missing": ["supplier_invoice"], "owner": "coverage", "invoice": None},
    2: {"headroom_before_minor": 250_000_000, "headroom_after_minor": 50_000_000,
        "missing": [], "owner": None, "invoice": "DOC-INV-01@1"},
}
EXPECTED_SOURCES = {
    "trade_finance": ("TRADE-01@1", "POL-TRADE-01@1"),
    "credit_risk": ("FAC-USD-01@1", "POL-CREDIT-01@1"),
    "compliance": ("INTAKE-01@1", "POL-COMPLIANCE-01@1"),
}


def check_packets(packets, expected):
    credit = packets["credit_risk"]
    observed = {fact["field"]: fact["value"] for fact in credit["facts"]}
    observed["missing"] = packets["compliance"]["missing_items"]
    observed["owner"] = "coverage" if packets["compliance"]["suggested_next_step"] == "request_invoice" else None
    invoice = expected["invoice"]
    refs = {}
    for desk, (source, policy) in EXPECTED_SOURCES.items():
        packet = packets[desk]
        evidence = {source}
        if invoice and desk != "credit_risk":
            evidence.add(invoice)
        refs[desk] = (
            set(packet["policy_refs"]) == {policy}
            and set(packet["evidence_refs"]) == evidence
            and all(fact["source_ref"] == source for fact in packet["facts"])
        )
    problems = [key for key in ("headroom_before_minor", "headroom_after_minor", "missing", "owner")
                if observed.get(key) != expected[key]]
    if any(not correct for correct in refs.values()):
        problems.append("unsupported_or_missing_citation")
    if packets["trade_finance"]["missing_items"] != expected["missing"]:
        problems.append("trade_invoice_status")
    return observed, refs, problems


def evaluate(mode):
    runs = []
    for revision, expected in EXPECTATIONS.items():
        case = snapshot("LC-001", "ORG_DEMO_01", complete=revision == 2)
        case["revision"] = revision
        started = perf_counter()
        result = prepare_packets(case, mode, run_id=identifier("EVAL"), authorize=lambda: None)
        seconds = round(perf_counter() - started, 4)
        observed, refs, problems = ({}, {}, [result.reason or result.status])
        if result.packets:
            observed, refs, problems = check_packets(result.packets, expected)
        verdict = "pass" if not problems else "fail"
        if result.status == "analysis_unavailable":
            verdict = "unverified"
        usage = [turn.get("usage", {}).get("total_tokens") for turn in result.observations]
        complete_usage = mode == "live" and len(usage) == result.model_calls > 0 and all(
            value is not None for value in usage
        )
        runs.append({
            "case_id": result.case_ref, "revision": revision, "run_id": result.run_id, "mode": mode,
            "policy_version": result.policy_version, "verdict": verdict, "failure_reasons": problems,
            "expected": expected, "observed": observed, "citation_checks": refs,
            "agent_wall_seconds": seconds, "tool_reads": result.tool_reads, "model_calls": result.model_calls,
            "observations": result.observations, "actual_total_tokens": sum(usage) if complete_usage else None,
            "missing_measurements": ["manual_wall_time", "active_staff_time"] + (
                [] if complete_usage else ["provider_token_usage"]
            ),
        })
    return {
        "mode": mode,
        "answer_key": "legal/case-answer-key.md",
        "scenarios": ["initial_file_without_invoice", "complete_amended_file"],
        "passed": sum(run["verdict"] == "pass" for run in runs),
        "total": len(runs),
        "unverified": sum(run["verdict"] == "unverified" for run in runs),
        "runs": runs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    score = evaluate(args.mode)
    output = args.output or Path(".clearance/evidence") / f"agent-utility-{args.mode}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
    print(f"{args.mode}: {score['passed']}/{score['total']} correct, {score['unverified']} unverified · {output}")
    if score["passed"] != score["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
