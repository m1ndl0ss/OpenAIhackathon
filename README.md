# Redwood

Redwood helps corporate banking staff prepare a request that needs several departments to agree. In the jury case, a relationship manager requests a USD 2 million letter of credit. The organizer sends work to Trade Finance, Credit Risk and Compliance. BRANE checks each model request, each desk signs its finding, and a separate officer makes the final decision. All cases are synthetic and issuance is simulated.

**Start with the [submission guide](SUBMISSION.md) or its [printable edition](output/pdf/redwood-submission.pdf).** The [37-second recorded walkthrough](docs/evidence/live-walkthrough.gif) shows the case from desk selection through issuance.

## Submission for the AI-Z track

| What the jury evaluates | What to open |
| --- | --- |
| **Technology and execution · 40 points.** Working agent, BRANE integration and human handoff. | [Run the demo](#run-from-a-fresh-clone) · [Architecture](docs/pitch/1_trust_boundaries.png) · [Recorded model calls, signatures and receipt](docs/evidence/submission-live.json) |
| **Legal research and governance · 40 points.** The agent’s legal position, department data classifications and implemented rules. | [Agent legal brief](output/pdf/redwood-legal-position.pdf) · [26 department analyses](research/bank-data-classification/README.md) · [Completed policy matrix CSV, 11 rules](submission/MAIN_Policy_Matrix_Template.csv) |
| **Business impact · 20 points.** Three-minute live demonstration, value and comparison with manual preparation. | [Pitch and team Q&A](docs/pitch.md) · [Business case and timing comparison](SUBMISSION.md#business-case) · [Utility scorecard](eval/utility-scorecard.csv) |
| **Mandatory security gate.** Five required scenarios and five team-written banking edge cases. | [Completed test evidence CSV](submission/MAIN_Five_Tests_Template.csv) · [Results for both versions of test five](SUBMISSION.md#governance-and-the-five-security-tests) · [Evidence index](docs/evidence/README.md) |

The two finished CSVs are in [submission/](submission/). The track description lists the deliverables on page 8 and the judging criteria on page 9. The participant brief adds the CSV format, the five edge cases and the three-minute demo. [Track description](docs/AI-Z-Track-Description.pdf) · [Participant brief](docs/MAIN_Participant_Starter_Kit/MAIN_Summit_AI-Z_Challenge_Brief.pdf)

![Redwood showing a payment request, the agent’s recommendation, its route and the assigned reviewers](docs/evidence/request-result.jpg)

## Give the jury a runnable copy

From a Git checkout, run `make submission`. It prints the path of a ZIP under `.clearance/submission/` built from the current commit. Send that ZIP through the organiser’s hand-in channel or give the jury read access to this private repository. The ZIP includes the runnable app, both completed CSVs, both Redwood PDFs and the recorded evidence. After extracting it, open `Redwood/README.md` for local links and run the commands below from the `Redwood` folder. The live demo uses the team’s credential.

## Run from a fresh clone

Install Python 3.11+ and Node 22.12+ with npm. Run these commands from the repository root.

```sh
make setup
make run
```

Open the [local demo on port 8000](http://127.0.0.1:8000) and choose **Coverage**. The desk picker supplies a demo identity. This mode uses local fixtures and requires no API key.

### Run the live BRANE rehearsal

After setup, copy `.env.example` to `.env` on a fresh clone and put the assigned AI-Z team credential in `BRANE_API_KEY`. Then start the live rehearsal.

```sh
make brane-check
make run-live
```

Open the [live console on port 8001](http://127.0.0.1:8001). It starts with a fresh synthetic database. The bank verifies the active policy before each model call. [Configuration example](.env.example) · [BRANE setup](policy/README.md)

## Walk the case

1. Choose **Coverage → LC-001 → Run analysis**. **Agent reply** shows the recommendation and sources. **Request routing** shows which desk prepared each finding.
2. Review the missing invoice as Compliance and place a hold. As Coverage, attach the invoice and rerun the case. Reviewers now sign revision 2.
3. With three current desk clearances, the assigned officer selects **Final approve**. Operations can then record one simulated issuance. [Full role-by-role walkthrough](docs/demo-guide.md#walk-the-case)

### Try a specialist desk

Choose **Corporate banking → Payments & Cash** for a second example, or use **New request → Payment exception triage → Fill demo example**. After submission, read the agent’s recommendation, send the finding for desk review and follow the named signers through final approval. The repo has 27 workflows and 54 seeded examples. [Payment walkthrough](docs/demo-guide.md#try-a-specialist-desk) · [All desks and case IDs](docs/department-workflows.md)

## What the evidence supports

- **Utility.** The live letter-of-credit rehearsal produced six cited drafts across two revisions in **29.55 seconds**. The team reports manual preparation took about twice as long, implying **roughly 59 seconds** for comparable work. The team supplied the ratio without separate stopwatch readings. A second live run took **47.63 seconds**. [Measurement and assumptions](SUBMISSION.md#business-case) · [Readiness rerun](docs/evidence/readiness-live.json)
- **Security.** The submitted workflow recorded a pass for each of the five gate scenarios and five edge cases within the scope described in the worksheet. The bank observed zero planted private fields across six outbound model requests. The gateway on its own missed a raw name variant. Both results are disclosed. [Submitted test results](submission/MAIN_Five_Tests_Template.csv) · [Security evidence and limitations](SUBMISSION.md#governance-and-the-five-security-tests)
- **Reach.** All 26 specialist workflows reached a signed outcome in a separate live rehearsal using scripted staff identities. BRANE reported 57 cloud calls and 12 local-model calls. Three restricted desks completed their tasks entirely in bank code. [Specialist run](docs/evidence/department-rehearsal-live.json)

## Repository guide

| Looking for | Location |
| --- | --- |
| Runnable application and invented cases | [Bank API and organizer](backend/) · [Staff console](console/) · [Synthetic cases](data/) |
| Governance and assurance | [Deployed policy](policy/) · [Case mandate and answer key](legal/case-answer-key.md) · [Reviewed submission evidence](docs/evidence/README.md) |
| Reproducing a result or developing the app | [Demo and developer commands](docs/demo-guide.md#developer-commands) · [Tests](tests/) · [Team plan](docs/team-build-plan.md) |
