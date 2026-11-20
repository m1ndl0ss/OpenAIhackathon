# Collect the challenge evidence

`make setup` creates three editable workbooks under `.clearance/evidence/` using the organisers’ column headers. `baseline.csv` and `hardened.csv` each contain T1–T5 and E1–E5, initially marked **UNVERIFIED**. `policy-matrix.csv` is ready for Ilaria's cited rules. Setup preserves existing workbooks.

Both fixture reports were generated with `make evidence` at integration commit `816853b`. E3 recorded blocked approval and issuance while Compliance held a complete file. E4 recorded a stale-revision rejection and one persisted receipt after concurrent retries and restart. The BRANE columns are empty because these checks ran on the local bank workflow. [E3/E4 results](workflow-fixture.csv)

The agent identified the missing invoice and Coverage as its owner on revision 1. On revision 2 it found the invoice. Both runs produced USD 500,000 remaining capacity and passed citation checks for all three desks. Each used eight local tool reads and three fixture turns. Provider usage, live routing and staff time are unmeasured. [Agent utility results](agent-utility-fixture.json)

| Owner | Inputs to the report |
| --- | --- |
| Matvei | Official T1–T5, plus E1 case isolation, E2 local/cloud boundary and E5 outage. Record actual policy versions and available redacted trace references for both policies. The official brief and CSV describe T5 differently. Retain the original wording and record AI-Z's clarification. |
| Nikita | `make evidence` runs E3 hold enforcement and E4 stale revision and duplicate finalisation checks against disposable fixture cases. Copy the observed results with their fixture labels. |
| Tasos | Observed utility, source quality, model usage and any unavailable measurements for the same case under each evaluated configuration. |
| Ilaria | Review the worksheets and [utility scorecard](../../eval/utility-scorecard.csv), keep missing observations visible, and publish the reviewed, redacted report here. |

The generated workbooks are private workspace files. Attach only reviewed exports to the submission. Keep generated tokens, raw prompts, personal data and unredacted provider exports out of Git.
