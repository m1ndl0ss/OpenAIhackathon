# Collect the challenge evidence

`make setup` creates three editable workbooks under `.clearance/evidence/` using the organisers’ column headers. `baseline.csv` and `hardened.csv` each contain T1–T5 and E1–E5, initially marked **UNVERIFIED**. `policy-matrix.csv` is ready for Ilaria's cited rules. Setup preserves existing workbooks.

| Owner | Inputs to the report |
| --- | --- |
| Matvei | Official T1–T5, plus E1 case isolation, E2 local/cloud boundary and E5 outage. Record actual policy versions and available redacted trace references for both policies. The official brief and CSV describe T5 differently. Retain the original wording and record AI-Z's clarification. |
| Nikita | `make evidence` runs E3 hold enforcement and E4 stale revision and duplicate finalisation checks against disposable fixture cases. Copy the observed results with their fixture labels. |
| Tasos | Observed utility, source quality, model usage and any unavailable measurements for the same case under each evaluated configuration. |
| Ilaria | Review the worksheets and [utility scorecard](../../eval/utility-scorecard.csv), keep missing observations visible, and publish the reviewed, redacted report here. |

The generated workbooks are private workspace files. Attach only reviewed exports to the submission. Keep generated tokens, raw prompts, personal data and unredacted provider exports out of Git.
