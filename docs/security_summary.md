# Security & BRANE Policy: Summary

Owner: Matvei · Branch: `security/brane-policy-v1` · Live policy: hardened-v2

## What was done

**Secrets hygiene**
- API key only in `.env` (git-ignored). `.env.example` has placeholders.
- Secret scan before every commit: 0 hits across 84 files, including git-ignored `evidence/raw/` and `local/`.

**Baseline captured first**
- Open department (25/25 categories `allow`) recorded before any change: **1/12 checks pass**.
- Saved as `policy/baseline-open.json` + baseline evidence run.

**BRANE policy as code**
- Per-category actions: identifiers → `placeholder`, civil IDs and GDPR Art. 9 → `local`, credentials and card numbers → `refuse`.
- 6 semantic rules: sanctions screening detail, indirect health context, protected attribute used in credit assessment, autonomous final decision, natural-person credit scoring, embedded instruction override.
- `scripts/apply_policy.py`: PUT, then read back and compare hash. A 200 alone is never treated as applied.
- `scripts/verify_policy.py`: drift gate. `run_checks.py` refuses to run if the live policy differs from the committed file (anyone with the team key can change it).

| Policy | Hash |
|---|---|
| baseline-open | `sha256:b0af864d48bd52c968e3e10bc7a6c4cf` |
| hardened-v1 | `sha256:4c293e4248d51401c51d9437d41ec60c` |
| hardened-v2 (live, verified by read-back) | `sha256:7238362ad6b930085f5f850bc1dbf6cf` |

**Evidence harness**
- `scripts/run_checks.py`: 20 checks. v2 ran all 20 three times (60 rows); v1 ran 16 checks across 7 run files (49 rows); the baseline was captured once, before hardening, over the 12 checks that existed then. Every CSV row carries the policy version and its hash; the UTC timestamp is in the filename and in the raw JSONL record.
- Three-state verdicts: PASS / FAIL / UNVERIFIED. A missing header is never a PASS.

## Results

| | Baseline | v1 | v2 |
|---|---|---|---|
| Checks passed | 1/12 | 13/16 | **18/20** |

3 runs per check on v1 and v2, identical results across runs. The baseline column is a single run: re-measuring it would mean reverting the live department.

The 2 remaining failures are BRANE product gaps, kept as FAIL with mitigations:
- **T3** name variants (raw BRANE): surname-first "DE VRIES, Jan" not detected. Mitigated by T3b (app-side tokeniser): PASS.
- **T3c** meaning preservation: over-detection replaced "expiry on" and "Beneficiary" (73 words in, 70 out). Mitigated by a pre-flight word-diff canary in the adapter contract.

Highlights on v2: T5a and E2 (indirect health) now route local; C3b refused by rule description alone; C3c (benign health mention) stays local, so the protected-attribute rule is targeted, not blanket.

## BRANE findings

1. **Surname-first names missed, tokens per spelling.** "DE VRIES, Jan" not detected; "Jan de Vries" and "J. de Vries" get different tokens. Fix: `scripts/case_tokeniser.py` replaces all known aliases with one `[[TOKEN]]` before BRANE. Token shape matters: word-like tokens get re-detected as names in some positions and not others (`SIGNATORY_1_ACCOUNT` survived 1 of 3, `CASE_ACCOUNT_A` 2 of 3), while `[[ACCT-A]]`, `#ACCT-A#` and `acct-ref-a` were all stable at 3 of 3. `[[…]]` is the shape we locked.
2. **Detector changes sentence meaning.** At `piiSensitivity: high`, ordinary words are labelled PERSON and replaced. Routing is correct, content is not, and no header reports it. Mitigation: compare outgoing preview to input word by word; refuse to send on any diff.
3. **Silent keyword cap.** BRANE keeps max 20 keywords per semantic rule and drops the rest while returning HTTP 200. Only read-back verification caught it (the first v2 draft was unapplicable for this reason).
4. **Wrong attribution header.** `X-Brane-Local-Cause` named the wrong cause on E3; undocumented `X-Brane-Policy-Triggers` was accurate.

## Deliverables

| File | What |
|---|---|
| `evidence/MAIN_Five_Tests_Template.csv` | T1–T5 + E1–E5, latest v2 run only |
| `evidence/clearance_policy_matrix.csv` | Policy matrix: 45 cells moved from expected to observed. Two target decisions corrected by evidence (CB-04 and CB-10, `BLOCK` → `LOCAL ONLY`); CB-05, CB-07 and CB-09 marked unverified because BRANE does not enforce them. Legal column byte-identical to Ilaria's original, kept alongside as `clearance_policy_matrix.source.csv` |
| `evidence/REPORT.md` | Full baseline / v1 / v2 comparison, findings, desk questions |
| `docs/brane_adapter_contract.md` | Contract + 5 acceptance tests for Tasos's adapter |
| `docs/demo_evidence.md` | Screen-ready blocks for the pitch slot |
| `evidence/superseded/` | Earlier iterations, kept but not citable |

## Open

- A1, A3, A4 need Nikita's API; A5 needs Tasos's adapter.
- CB-09 (client commercial terms) has no BRANE rule.
- AI-Z desk questions (8 in `REPORT.md` §9): which T5 is graded, post-policy egress observation, `Policy-Triggers` header, the v1 health-detector miss, `E1`–`E5` vs `A1`–`A5` numbering, surname-first false negative, meaning change, keyword cap.
- Rotate the team API key.
