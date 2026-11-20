# Redwood | Corporate banking through BRANE

A relationship manager receives a USD 2 million import letter-of-credit request. Redwood prepares a cited file for Trade Finance, Credit Risk and Compliance. The organizer routes the work, staff sign against the current revision, a mandated officer decides and Operations records one simulated issuance. Redwood also has 26 specialist workflows spanning the rest of the bank. The demo uses synthetic data throughout. [AI-Z challenge brief and judging criteria](docs/AI-Z-Track-Description.pdf)

## Hand-in at a glance

| The brief asks for | Where to find it |
| --- | --- |
| A working AI agent with BRANE integration | `make run-live` (steps below) · [Drafting loop](backend/agent/runtime.py) · [Firewall adapter](backend/brane_client.py) · [Live run](docs/evidence/submission-live.json) |
| Legal research with concrete sources | [Legal position of the submitted agent](docs/legal-position.md) · [Corporate banking legal research](research/bank-data-classification/README.md) · legal-source column of the policy matrix |
| Policy matrix | [Submission policy matrix](docs/evidence/submission-policy-matrix.csv): 11 rules with sources, technical controls, observed results and product gaps |
| Five security tests and five edge cases | [Submission test worksheet](docs/evidence/submission-tests.csv) · [Gateway-only worksheet](evidence/MAIN_Five_Tests_Template.csv) · [Full measured comparison](evidence/REPORT.md) |
| Live demo and business case | The sections below · [Pitch script and evidence for every claim](docs/pitch.md) |
| At least three justified, implemented rules | 11 rules; enforcement and evidence per rule in the matrix |
| An agent that performs its task repeatedly | Both case revisions live, 26 specialist desks in a live rehearsal, 261 automated tests |
| Synthetic data only | Every case, identity and document in `data/` is invented |

The security evidence is frozen at tag [`evidence-freeze-v1`](https://github.com/m1ndl0ss/OpenAIhackathon/tree/evidence-freeze-v1), checked against policy `hardened-v2` (`sha256:7238362ad6b930085f5f850bc1dbf6cf`).

## Open the demo

From the repository root, run `make setup` with Python 3.11+ and Node 22.12+. For the live rehearsal, copy `.env.example` to `.env` on a fresh clone and enter the team's AI-Z credential in `BRANE_API_KEY`. The sample already names the assigned endpoint, OpenAI model and policy. An existing configured checkout can go straight to the two commands below.

```sh
make brane-check
make run-live
```

Open the local rehearsal and click **New request**. Choose **Payment exception triage**, click **Fill demo example** and edit the payment amount.

1. Click **Submit request**. When the organizer finishes, **Agent reply** shows the recommended next step, the wording returned by the agent and the supporting record. For the first payment example, read the recommendation to confirm the return match and the account-closed reason. Open **Review findings and sources** to inspect the policy and handover drafts before sending anything to the reviewers.
2. **Send for desk review** delivers the packet to Sam Reed in Payments and Amir Cole in Operations. Click **Review finding** for Sam, inspect the current evidence, enter a reason and click **Sign desk finding**. Click **Review as Amir Cole** and sign the Operations finding. **Use demo reason** supplies an editable example for either person.
3. With **2 of 2 signed**, click **Final approve** beside Ari Fox. Enter Ari’s decision reason and confirm with **Final approve**. The dashboard shows **Approved by Ari Fox** and the case history records the individual signatures.

For the preloaded letter-of-credit walkthrough, choose **Coverage → LC-001 → Run analysis**. Sealing a preloaded case sends it to its reviewers automatically. Each fresh live rehearsal has its own temporary database. For an offline walkthrough use `make run` and port 8000. [Live rehearsal](http://127.0.0.1:8001) · [Offline console](http://127.0.0.1:8000) · [Full click-through guide](README.md#walk-the-case)

## What to show the jury

| On screen | What to demonstrate |
| --- | --- |
| Coverage dashboard | Submit LC-001. The organizer runs three desk tasks. Each prepares a draft for a different reviewer. |
| Credit Risk and Compliance | Credit sees USD 2.5m available before issuance and USD 500k remaining afterward. Compliance finds a missing supplier invoice, selects **Hold** and requests it from Coverage. The officer cannot approve the held file. |
| Coverage and the three desks | Attach the invoice to the request and run revision 2. The old signature is historical. Trade and Credit clear the new file. Compliance selects its hold and the invoice it reviewed before clearing. |
| Mandated officer and Operations | Show three signatures on the same revision. The officer records the decision. Operations records the simulated receipt. A retry returns the same receipt. |
| Security evidence | Show one clean OpenAI route, a protected case, the raw-firewall failures, and the outage trace. In the outage the bank attempted its policy read, submitted zero model requests and sealed nothing. |

The letter-of-credit backup is a captioned sequence of actual browser captures from a separate live run on 20 November 2026, recorded with the previous desk picker. Its second revision is `RUN-5f7355181dc94cdb88473c1ddd5fe978`. The machine-readable rehearsal below has its own run IDs. [Play the 37-second backup](docs/evidence/live-walkthrough.gif)

## Show another department

Choose **Corporate banking → Payments & Cash**, open **PAY-001** and run analysis. The organizer prepares an evidence packet, a policy check and an internal handover. The analyst and Operations each sign. A different Payments approver records the return match or refers the file. **Risk & control → AML & Financial Crime** shows the same organizer working entirely inside the application. The case overview displays the observed routes and model-call count. [See the payment dashboard](docs/evidence/specialist-workflow.jpg) · [All desks and cases](docs/department-workflows.md)

A separate live rehearsal took the first example at each of the 26 specialist desks through drafting, staff signatures and the final internal outcome. BRANE handled 69 calls for 23 workflows. It reported 57 cloud routes and 12 local-model routes. M&A, financial crime and surveillance completed nine internal tasks with zero model calls. Both examples at every desk also have automated fixture coverage. [Specialist run results](docs/evidence/department-rehearsal-live.json) · [Tests for both examples](tests/test_department_workflows.py)

## What ran in the letter-of-credit case

The bank owns the facility arithmetic, evidence lookup, access checks and approval rules. For each desk, the model chooses between two approved wordings. The model request contains the desk, next-step code and those wordings. The adapter accepts only the bank's fixed drafting messages and verifies the active firewall policy before each call. The bank validates the reply and attaches the locally computed facts and source references. A response outside the approved choices leaves the file unsealed. [Architecture diagram](docs/corporate-banking-architecture.png) · [Drafting loop](backend/agent/runtime.py) · [Firewall adapter](backend/brane_client.py)

On 20 November the committed application ran both case revisions through `openrouter:openai/gpt-6-luna` under `hardened-v2`. All six responses reported a cloud route. Three reported pseudonymisation and three reported direct passage. Each response has a provider request ID, routing headers, token usage and the policy digest read from the department immediately before the request. BRANE supplied those headers. The team had no downstream provider packet capture. [Live run and receipts](docs/evidence/submission-live.json) · [Application revision](https://github.com/m1ndl0ss/OpenAIhackathon/commit/3e3de3519102510855f3840772777c48994ed9f5)

| Measured at the staff API | Revision 1 | Revision 2 |
| --- | ---: | ---: |
| Desk packets matching the case answer key and source checks | 3 of 3 | 3 of 3 |
| Local tool reads / model calls | 8 / 3 | 8 / 3 |
| Elapsed time from submission through packet and source checks | 15.85 s | 13.70 s |
| Provider-reported tokens | 494 | 535 |
| Invoice result | Missing, Coverage owns the request | Attached and cited |
| Capacity after proposed issuance | USD 500,000 | USD 500,000 |

The measured API rehearsal used six distinct scripted staff identities. It recorded a rejected decision while held, a rejected stale decision, three current desk clearances, one final approval and one durable simulated receipt. A separate fixture check repeats concurrent decisions and issuance after restarting the application. [Live workflow](docs/evidence/submission-live.json) · [Restart and concurrency checks](docs/evidence/workflow-fixture.csv) · [Independent case answer key](legal/case-answer-key.md)

## Governance and the five security tests

The submission matrix contains eleven rules with their sources, technical controls, observed results and remaining gaps. Examples from the implemented case follow. [Submission policy matrix](docs/evidence/submission-policy-matrix.csv) · [Corporate banking legal research](research/bank-data-classification/README.md)

- **Minimise identifying and commercial data.** A private desk message and an invoice note each contained two forms of a synthetic name and a repeated email. Both notes were visible to the intended staff. The observed outbound requests contained zero matches for those markers or for the tested financial fields. GDPR Articles 5 and 25 inform the personal-data control. Keeping client amounts and facility references inside the bank is a separate confidentiality decision. [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/) · [Live transport observations](docs/evidence/submission-live.json)
- **Restrict sensitive evidence.** The department routes special-category information and detailed screening notes locally in the documented cases. Other desks receive a disposition. The matrix distinguishes personal-data safeguards from the narrower statutory restrictions on disclosing AML reporting and analysis. [GDPR Article 9](https://eur-lex.europa.eu/eli/reg/2016/679/) · [Directive (EU) 2015/849, Article 39](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A32015L0849) · [Security observations](evidence/REPORT.md)
- **Keep decision authority with the bank.** The synthetic mandate requires three current desk clearances followed by the officer's decision. A separate Operations identity records the issuance. The gateway also refused an autonomous-decision request in the security team's run. [Bank mandate and answer key](legal/case-answer-key.md) · [Measured policy rules](docs/evidence/submission-policy-matrix.csv)
- **Stop when the firewall cannot be verified.** The app checks the configured policy digest and enabled rules before sending a model request. A controlled outage denied network access at the Python socket boundary. Only a read of the assigned firewall was attempted. [Outage trace](docs/evidence/firewall-outage.json)

| Official gate | Result and scope |
| --- | --- |
| T1 · Permitted request | The live Credit Risk draft reached OpenAI with a clean cloud verdict on both revisions. The resulting packets matched the answer key. |
| T2 · Protected data | The live bank omitted the tested private fields before BRANE. The standalone suite also observed placeholder routing and inspected a separate policy preview. |
| T3 · Repeated details | The integrated bank passed the repeated-contact and name-form check. The standalone firewall **failed** one raw name variant. Its separate, locally tokenised T3b passed. |
| T4 · Untrusted instructions | The security team's recorded inputs stayed local. The letter-of-credit workflow accepts seven bank-owned message combinations. Each specialist workflow checks its own registered tasks and wordings. Human notes and source documents stay out of the model input. |
| T5 · Firewall unavailable | The network-denied bank attempted one policy GET, zero model POSTs and zero other destinations. The case stayed unsealed. The security client also passed 15 fault runs and three healthy controls. The client process contacted only each scenario’s assigned destination. [Security client results](docs/evidence/brane-check-failure.csv) |

The security team's standalone suite went from **1/12 on the delivered open policy** to **17 of 20 clean on `hardened-v2`**, with every check run three times. Two failures stay visible: raw name coverage (T3) and preservation of ordinary trade wording (T3c). Both matter only if a future workflow forwards document text. The submitted app sends prewritten drafting inputs and accepts only exact permitted replies. One check, C3c, is non-deterministic: BRANE's semantic judge refused a harmless note once in three runs, so it over-blocks rather than leaks. Every check records BRANE's dry-run and live decisions side by side, and 41 of 42 comparable rows agree. A red team then ran 30 attacks: 20 against the firewall and our masking (19 held, 1 unverified) and 10 against the application (10 held). The one bypass found on the way, X10 in our own token handling, is fixed and re-tested. A drift test shows that a tampered policy stops every run before any model call. [Final ten-row protocol](docs/evidence/submission-tests.csv) · [Gateway results](evidence/MAIN_Five_Tests_Template.csv) · [Full measured comparison](evidence/REPORT.md) · [Red-team findings](docs/redteam_findings.md)

## Business case

**Who buys it.** The head of trade finance operations, with the CISO and the data protection officer co-signing. For the first two it removes rework between desks. For the last two it replaces unapproved AI use with a governed path.

**1. Staff already use AI, and unapproved use is expensive.** In May 2026 a US bank filed the first SEC disclosure caused by an employee pasting customer names, Social Security numbers and dates of birth into an unapproved AI app. The Dutch Data Protection Authority received dozens of similar reports in 2025, more than in 2024. IBM's 2025 Cost of a Data Breach report puts the average breach in the financial industry at USD 5.56 million, and organisations with high levels of shadow AI paid on average USD 670,000 more per breach. Redwood gives staff an AI path the bank can prove is safe: zero tested private fields left the bank across six live model requests, and nothing is sent when BRANE cannot be verified. [Live transport observation](docs/evidence/submission-live.json) · [Outage trace](docs/evidence/firewall-outage.json) · [Sources for these figures](docs/pitch.md#where-every-claim-comes-from)

**2. Rework between desks when a document changes (measured).** In the letter-of-credit case the organizer prepared six cited desk packets over two revisions, identified the missing invoice and its owner, and stopped staff from acting on an old signature. The two rounds took **29.55 seconds** and used **1,029 tokens**. This measures preparation and validation. Staff reading, judgment and sign-off still take time. [Utility scorecard](eval/utility-scorecard.csv)

**3. One control plane for the whole bank (measured).** The same organizer, gateway, BRANE policy and evidence harness run 27 workflows. In the live specialist rehearsal BRANE handled 69 calls for 23 workflows, with 57 cloud and 12 local-model routes, and three restricted desks needed no model call at all. A new desk registers its tasks and approved wordings and inherits the existing controls. [Specialist run results](docs/evidence/department-rehearsal-live.json)

**Planning example (assumptions, not measurements).** Assume 27 workflows with 1,000 cases each per year, three staff minutes saved per case and EUR 60 per staff-hour. That is 1,350 staff-hours, or about EUR 81,000 of capacity per year. At an assumed EUR 0.10 per case in variable costs (EUR 2,700), about EUR 78,000 remains before fixed costs. For the letter-of-credit desk alone at 500 cases, the same assumptions give EUR 1,500. The larger figure is the avoided incident in point 1. The team did not measure a manual comparison or receive a provider invoice. A pilot would time manual and assisted cases of similar complexity, and compare error corrections and total operating cost.

## Reproduce the evidence

```sh
make test
make evidence
make live-evidence
```

The first two commands run locally. The third uses the team credential to exercise both revisions through the real staff API and BRANE on a disposable database. The generated reports are under `.clearance/evidence/`. The committed evidence records the original run with its timestamp and receipt. [Evidence index](docs/evidence/README.md) · [Deployed policy definition](policy/hardened-v2.json)
