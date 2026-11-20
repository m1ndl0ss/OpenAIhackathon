# Security & BRANE Policy: Summary

Owner: Matvei · Branch: `security/brane-policy-v1` · Live policy: hardened-v2

This records the standalone security workstream. The integrated bank, outage result and revised evidence matrix are available in the [submission guide](../SUBMISSION.md).

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
| Policy checks passed | 1/12 | 13/16 | **18/20** |
| A5 check-failure scenarios | – | – | **6/6 (18/18 runs)** |

3 runs per check on v1 and v2, identical results across runs. The baseline column is a single run: re-measuring it would mean reverting the live department. A5 is a separate harness (`scripts/check_failure_test.py`) because it injects faults rather than prompts.

### Test 5 is defined three ways by AI-Z; all three are now evidenced

| Source | Its definition of test 5 | Our evidence |
|---|---|---|
| **Participant Brief**, Mandatory Security Gate | "Special category / local — GDPR Art. 9 or non-exportable case kept on the local GPU model or refused, never sent to cloud" | **T5a PASS** 3/3 on v2: routes `local`, `Semantic-Matches: INDIRECT_HEALTH_CONTEXT` |
| **Five-tests CSV template**, T5 row | "Check unavailable / unverifiable: no unverified external model send; routes local with cause header" | **T5b PASS** 3/3: HTTP 422 rather than answering from an unverifiable sanctions screening |
| **Track description** §03 and §06 | "Check failure: if the protection check is unavailable, the request is not sent. An automatic fallback to the cloud model fails this test" | **T5c/A5 PASS** 18/18: DNS failure, connection refused, timeout, HTTP 503, and HTTP 200 with a completion but no `X-Brane-Routed-To`, plus a healthy control |

The three are not interchangeable. T5b is an unavailable *business* check with BRANE healthy; the track's test is BRANE *itself* being gone. Egress in A5 is observed by a `sys.addaudithook` on `socket.connect` / `socket.getaddrinfo` — independent of the client's own logging — and the only hosts contacted across the whole run were the scenario endpoints and `brane.ai-z.io`. Zero contact with any model provider.

**A5 also produced a finding:** the same test against the raw transport fails 0/18. An HTTP 200 carrying a completion with no `X-Brane-Routed-To` is indistinguishable from a governed answer at the transport layer — the governed client classifies it `unavailable` and discards 121 chars; the raw transport hands them to the caller. That is now a MUST with evidence in the adapter contract, and `brane_client.classify_outcome()` is the reference implementation.

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
| `evidence/clearance_policy_matrix.csv` | Eleven rules with Ilaria’s task rationale and legal sources. CB-04 routes classification locally and blocks use of protected attributes in a commercial assessment. CB-10 calls for local handling of civil IDs and records a detector misclassification. CB-07 links the independently observed outage runs. |
| `evidence/REPORT.md` | Full baseline / v1 / v2 comparison, findings, desk questions |
| `docs/brane_adapter_contract.md` | Contract + 5 acceptance tests for Tasos's adapter |
| `docs/demo_evidence.md` | Screen-ready blocks for the pitch slot |
| `evidence/superseded/` | Earlier iterations, kept but not citable |

## Open

- The staff API records case isolation, holds, concurrent retries and the permitted agent run. The merged A5 harness records destinations visible to the client process. OS-wide traffic remains outside the measurement. [Staff test worksheet](evidence/submission-tests.csv) · [Live case and receipt](evidence/submission-live.json) · [18-run A5 verification](evidence/brane-check-failure.csv)
- CB-09 (client commercial terms) has no BRANE rule.
- AI-Z desk questions (8 in `REPORT.md`): which T5 is graded, post-policy egress observation, `Policy-Triggers` header, the v1 health-detector miss, `E1`–`E5` vs `A1`–`A5` numbering, surname-first false negative, meaning change, keyword cap.
- Rotate the team API key.
