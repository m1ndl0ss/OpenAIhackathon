"""Run the two bank workflow checks and export their observations in the organisers' CSV format."""

import argparse
import csv
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/MAIN_Participant_Starter_Kit/MAIN_Five_Tests_Template.csv"
CHECKS = [
    ("E3", "test_e3_independent_compliance_hold", "Independent Compliance hold on a complete file",
     "Final approval and issuance stay blocked until the owning reviewer releases the hold.",
     "LC-002; current invoice, Trade and Credit cleared, independent Compliance hold."),
    ("E4", "test_e4_revision_retries_and_restart", "New invoice, stale decision and concurrent retries",
     "A stale decision fails. One approval event and one receipt survive retries and restart.",
     "LC-001; material invoice amendment, three renewed clears, two concurrent submissions."),
]


def record_for(report, test_name):
    case = report.find(f".//testcase[@name='{test_name}']") if report is not None else None
    if case is None:
        return "UNVERIFIED", "Pytest did not produce a result for this check. Inspect the test output."
    if case.find("error") is not None or case.find("skipped") is not None:
        return "UNVERIFIED", "The fixture setup failed or the test was skipped. Inspect the test output."
    if case.find("failure") is not None:
        return "FAIL", "An assertion or test operation failed. Inspect the test output for the failing step."
    observed = case.find("./properties/property[@name='observed']")
    if observed is None:
        return "UNVERIFIED", "No observations were captured."
    return "PASS", observed.get("value")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Path for the E3/E4 CSV.")
    args = parser.parse_args()
    with TemporaryDirectory() as directory:
        xml_path = Path(directory) / "observations.xml"
        command = [sys.executable, "-m", "pytest", "-q", "-o", "junit_family=legacy",
                   "--junitxml", str(xml_path)]
        command.extend(f"tests/test_trade_workflow.py::{check[1]}" for check in CHECKS)
        result = subprocess.run(command, cwd=ROOT, check=False)
        report = ET.parse(xml_path).getroot() if xml_path.is_file() else None

    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, cwd=ROOT, text=True)
    revision = git.stdout.strip() if git.returncode == 0 else "unknown"
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, cwd=ROOT, text=True)
    if dirty.returncode == 0 and dirty.stdout:
        revision += " + working-tree changes"
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    passed = True
    with TEMPLATE.open(encoding="utf-8-sig", newline="") as template, args.output.open(
        "w", encoding="utf-8", newline=""
    ) as out:
        writer = csv.writer(out)
        writer.writerow(next(csv.reader(template)))
        for check, test_name, scenario, expected, inputs in CHECKS:
            verdict, observed = record_for(report, test_name)
            writer.writerow([
                check, scenario, expected, inputs, "", "", "",
                observed + " Bank API check in fixture mode; no BRANE or model observation.",
                verdict, f"fixture workflow v1 | git {revision} | {timestamp}",
            ])
            passed = passed and verdict == "PASS"
    print(f"Wrote {args.output}")
    return result.returncode or (0 if passed else 1)


if __name__ == "__main__":
    raise SystemExit(main())
