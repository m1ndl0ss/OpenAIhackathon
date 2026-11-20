# Superseded runs

These runs are kept because spec §10 says to keep every run, including differences and
failures. They are **not** part of the evidence set and must not be cited: each was
produced by a harness or tokeniser version that has since been corrected, so their
verdicts measure our own bugs rather than BRANE's behaviour.

The policy under test was `hardened-v1`
(`sha256:4c293e4248d51401c51d9437d41ec60c`) throughout — unchanged across all of them.

| Runs | Why superseded |
| --- | --- |
| `…162529Z`, `…162555Z`, `…162616Z` | First run of the four added checks. `T4c` read `prompt_injection` instead of the API's `promptInjection`, so it logged `score=None`; `C1` demanded the `PASSWORD` label specifically and recorded UNVERIFIED when BRANE refused via the sibling `SECRET_KEY` label; `T3b` conflated the leak and consistency objectives into one unhelpful FAIL. |
| `…162905Z`, `…162930Z`, `…162949Z` | Verifiers corrected, but `T3b` still FAILed: the token `SIGNATORY_1_ACCOUNT` was re-detected by BRANE as `PERSON` in 2 of 3 positions. |
| `…163159Z`, `…163221Z`, `…163241Z` | Identifier tokens renamed to `CASE_ACCOUNT_A` etc. Still FAILed at 2 of 3 — the person-like prefix was not the whole cause. |
| `…163539Z`, `…163559Z`, `…163617Z` | Identifier tokens bracketed (`[[ACCT-A]]`, stable 3/3), but the word-like person token `SIGNATORY_1` was then re-detected as part of the span `"confirms SIGNATORY_1"`, which also deleted the verb from the outgoing payload. |

Two A5 check-failure runs are also here:

| Run | Why superseded |
| --- | --- |
| `redwood-A5-check-failure_…174648Z` | First version of the A5 test. Scenarios b-e used `http://` endpoints, which the client rejects before dialling, so they recorded **no network activity at all** and passed without exercising their failure modes. The test now fails any fault scenario that never reaches the network. |
| `redwood-A5-check-failure_…174815Z` | Correct results (18/18), but produced before the static endpoint check was scoped to code and configuration. Re-run as `…175417Z` against the current repo state. |
| `redwood-A5-check-failure_…174905Z` | First raw-client contrast run. Correct verdicts (0/18) but every scenario reported only "outcome=None", which buried the one finding that matters. Re-run as `…175012Z`, which names the missing classification and the 121 leaked characters. |

The findings these runs produced are reported properly in `../REPORT.md` §4.5 (token
shape determines whether BRANE re-detects an app-side token) and §5. The
authoritative sets are:

- `../baseline_run.csv` — open baseline, 12 checks, 1 run
- `../redwood-hardened-v1_20261120T1553*.csv` / `1557*.csv` — hardened, 12 checks, 3 runs
- `../redwood-hardened-v1_20261120T161953Z.csv` — T1 control re-run
- `../redwood-hardened-v1_20261120T1639*.csv` — hardened, the 4 added checks, 3 runs
- `../redwood-hardened-v2_20261120T165*.csv` — hardened-v2, 20 checks, 3 runs
- `../redwood-A5-check-failure_20261120T175417Z.csv` — A5, governed client, 18/18
- `../redwood-A5-check-failure_20261120T175012Z.csv` — A5, raw transport, 0/18 (the contrast)
