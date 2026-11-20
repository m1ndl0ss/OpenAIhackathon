# Redwood | Corporate banking through BRANE

A relationship manager receives a USD 2 million import letter-of-credit request. Redwood prepares a cited file for Trade Finance, Credit Risk and Compliance. The organizer routes the work, staff sign against the current revision, a mandated officer decides and Operations records one simulated issuance. Redwood also has 26 specialist workflows spanning the rest of the bank. The demo uses synthetic data throughout. [AI-Z challenge brief and judging criteria](docs/AI-Z-Track-Description.pdf)

## Hand-in at a glance

| Track requirement | Redwood submission |
| --- | --- |
| Working agent and a visible human decision | [Live setup and demo](#open-the-demo) · [Organizer and drafting](backend/agent/runtime.py) · [BRANE adapter](backend/brane_client.py) · [Two live revisions, signed decision and simulated receipt](docs/evidence/submission-live.json) |
| Legal research with traceable sources | [Legal position of the agent](docs/legal-position.md) · [One-page legal PDF](output/pdf/redwood-legal-position.pdf) · [26 department analyses](research/bank-data-classification/README.md) |
| Policy matrix with at least three justified, implemented protections | [Completed policy matrix CSV](submission/MAIN_Policy_Matrix_Template.csv). Eleven rules list the legal basis, control, observed result and remaining gaps. Examples include scoped access, human approval and stopping when BRANE is unavailable. |
| Three-minute live demo and business case | [Presenter script and Q&A](docs/pitch.md) · [Business case and manual comparison](#business-case) · [Recorded backup](docs/evidence/live-walkthrough.gif) |
| Pass/fail security gate, plus five team-written domain cases | [Completed test evidence CSV](submission/MAIN_Five_Tests_Template.csv). The ten rows include the applicable route or reason no call was sent, outcome, utility and policy version. [Both definitions of T5 and the T3 limitation](#governance-and-the-five-security-tests) |
| Repeatable runs on synthetic data | [Case fixtures](data/) · [26 specialist outcomes](docs/evidence/department-rehearsal-live.json) · [Tests](tests/). Bank actions result in internal simulated records. |

The track assigns 40 points to technology, 40 to legal research and governance, and 20 to business impact. An impermissible transfer fails the security gate. The organiser lists **Saturday 21 November 2026, 10:30 CET** for submission and **15:00 CET** for finals. The two completed CSVs use the organiser’s filenames. The runnable app and the live presentation are also part of the hand-in. [Track description, pp. 8–9](docs/AI-Z-Track-Description.pdf) · [Participant brief, pp. 1–2](docs/MAIN_Participant_Starter_Kit/MAIN_Summit_AI-Z_Challenge_Brief.pdf) · [Starter-kit checklist](docs/MAIN_Participant_Starter_Kit/starter-kit/README.md#4-submission-checklist-saturday-21-nov-1030-cet)

From a Git checkout, `make submission` builds the runnable ZIP for judges without repository access. Extract it and open `Redwood/README.md` to follow local evidence links. The links inside the printable PDFs open the repository or the cited public sources.

The team froze the security evidence against the `hardened-v2` policy, digest `sha256:7238362ad6b930085f5f850bc1dbf6cf`. [Evidence freeze](https://github.com/nickdatak/OpenAIhackathon/tree/evidence-freeze-v1)

In the recorded approval, Trade Finance, Credit Risk and Compliance have signed revision 2 of LC-001. Eva Lin has recorded the final decision. [Signed case dashboard](docs/evidence/signed-letter-of-credit.jpg)

## Open the demo

From the repository root, run `make setup` with Python 3.11+ and Node 22.12+. For the live rehearsal, copy `.env.example` to `.env` on a fresh clone and enter the team's AI-Z credential in `BRANE_API_KEY`. The sample already names the assigned endpoint, OpenAI model and policy. An existing configured checkout can go straight to the two commands below.

```sh
make brane-check
make run-live
```

Open the [live staff console](http://127.0.0.1:8001), choose **Coverage**, select **LC-001** and click **Run analysis**. Read **Agent reply**, **Request routing** and the source for the missing invoice. Each fresh live launch starts with its own synthetic database. For a credential-free fixture walkthrough, use `make run` after setup and open [port 8000](http://127.0.0.1:8000).

Use the three-minute script with one presenter driving. Start the live run during the introduction. While the security presenter explains BRANE, Coverage supplies the invoice and reruns the case. The three desks sign the current revision. Return to the live dashboard for the officer’s **Final approve**. If the service is unavailable, show the labelled recording and outage evidence. [Role-by-role instructions](docs/demo-guide.md#walk-the-case) · [Stage script](docs/pitch.md) · [Outage trace](docs/evidence/firewall-outage.json)

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

The bank owns the facility arithmetic, evidence lookup, access checks and approval rules. For each desk, the model chooses between two approved wordings. The model request contains the desk, next-step code and those wordings. The adapter accepts only the bank's fixed drafting messages and verifies the active firewall policy before each call. The bank validates the reply and attaches the locally computed facts and source references. A response outside the approved choices leaves the file unsealed. [Implemented trust boundaries](docs/pitch/1_trust_boundaries.png) · [Drafting loop](backend/agent/runtime.py) · [Firewall adapter](backend/brane_client.py)

On 20 November the committed application ran both case revisions through `openrouter:openai/gpt-6-luna` under `hardened-v2`. All six responses reported a cloud route. Three reported pseudonymisation and three reported direct passage. Each response has a provider request ID, routing headers, token usage and the policy digest read from the department immediately before the request. BRANE supplied those headers. The team had no downstream provider packet capture. [Live run and receipts](docs/evidence/submission-live.json) · [Application revision](https://github.com/nickdatak/OpenAIhackathon/commit/3e3de3519102510855f3840772777c48994ed9f5)

| Measured at the staff API | Revision 1 | Revision 2 |
| --- | ---: | ---: |
| Desk packets matching the case answer key and source checks | 3 of 3 | 3 of 3 |
| Local tool reads / model calls | 8 / 3 | 8 / 3 |
| Elapsed time from submission through packet and source checks | 15.85 s | 13.70 s |
| Provider-reported tokens | 494 | 535 |
| Invoice result | Missing, Coverage owns the request | Attached and cited |
| Capacity after proposed issuance | USD 500,000 | USD 500,000 |

The measured API rehearsal used six distinct scripted staff identities. It recorded a rejected decision while held, a rejected stale decision, three current desk clearances, one final approval and one durable simulated receipt. A separate fixture check repeats concurrent decisions and issuance after restarting the application. [Live workflow](docs/evidence/submission-live.json) · [Restart and concurrency checks](docs/evidence/workflow-fixture.csv) · [Independent case answer key](legal/case-answer-key.md)

A fresh readiness run on 21 November in Maastricht repeated the same two revisions in **24.571 s and 23.063 s** (47.63 s total). All six citation checks passed, the bank recorded zero matches for its planted private fields across six model calls, and Operations recorded one simulated receipt. The manual comparison below refers to the original 29.55-second run. [Readiness rerun](docs/evidence/readiness-live.json)

## Bounded autonomy

The organizer runs three drafting agents, one each for Trade Finance, Credit Risk and Compliance. Bank code reads the permitted evidence, computes the facility headroom and determines the next-step code. At the strictest setting used here, each agent makes a real model call through BRANE to choose one of two permitted sentences for that step. Bank code validates the reply, attaches figures and citations and makes the recommendation available to the reviewer. A rules engine could select a sentence at this setting. The deployment choice is how much discretion to delegate while keeping evidence access, arithmetic and signatures under bank control. [Drafting loop](backend/agent/runtime.py) · [Live responses](docs/evidence/submission-live.json)

The security team separately exercised the live **hardened-v2** policy on realistic synthetic document text, including invoice wording, personal data and health-related language. Those trials reveal both protection and masking errors. A next use to evaluate is a model drafting a discrepancy note from an approved invoice excerpt. A bank would first authorise that text, test the quality of its citations and the outbound data, and verify its legal basis. The current letter-of-credit demo sends bank-authored drafting prompts. [Policy](policy/hardened-v2.json) · [Document-text test results](evidence/MAIN_Five_Tests_Template.csv) · [Legal position](docs/legal-position.md)

Routing applies to individual tasks. The specialist rehearsal recorded **12 local-model calls across ten workflows**, including the KYC handover and two Credit & Counterparty Risk tasks. M&A, AML & Financial Crime and Regulatory Surveillance each completed three bank-side tasks with **zero model calls**. Their reviewers still received drafts for signature. [Task-level route observations](docs/evidence/department-rehearsal-live.json)

## Governance and the five security tests

The submitted agent has its own assessment of controller and processor roles, overseas transfers, pseudonymisation, the DPIA and AI Act classification. The desk inventory and policy matrix document how those judgments apply to specific records. [Agent legal position](docs/legal-position.md) · [Desk research](research/bank-data-classification/README.md) · [Policy matrix](submission/MAIN_Policy_Matrix_Template.csv)

The submission matrix contains eleven rules with their sources, technical controls, observed results and remaining gaps. Examples from the implemented case follow. [Submission policy matrix](submission/MAIN_Policy_Matrix_Template.csv) · [Corporate banking legal research](research/bank-data-classification/README.md)

- **Minimise identifying and commercial data.** A private desk message and an invoice note each contained two forms of a synthetic name and a repeated email. Both notes were visible to the intended staff. The observed outbound requests contained zero matches for those markers or for the tested financial fields. GDPR Articles 5 and 25 inform the personal-data control. Keeping client amounts and facility references inside the bank is a separate confidentiality decision. [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/) · [Live transport observations](docs/evidence/submission-live.json)
- **Restrict sensitive evidence.** The department routes special-category information and detailed screening notes locally in the documented cases. Other desks receive a disposition. The matrix distinguishes personal-data safeguards from the narrower statutory restrictions on disclosing AML reporting and analysis. [GDPR Article 9](https://eur-lex.europa.eu/eli/reg/2016/679/) · [Directive (EU) 2015/849, Article 39](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A32015L0849) · [Security observations](evidence/REPORT.md)
- **Keep decision authority with the bank.** The synthetic mandate requires three current desk clearances followed by the officer's decision. A separate Operations identity records the issuance. The gateway also refused an autonomous-decision request in the security team's run. [Bank mandate and answer key](legal/case-answer-key.md) · [Measured policy rules](submission/MAIN_Policy_Matrix_Template.csv)
- **Stop when the firewall cannot be verified.** The app checks the configured policy digest and enabled rules before sending a model request. A controlled outage denied network access at the Python socket boundary. Only a read of the assigned firewall was attempted. [Outage trace](docs/evidence/firewall-outage.json)

| Official gate | Result and scope |
| --- | --- |
| T1 · Permitted request | The live Credit Risk draft reached OpenAI with a clean cloud verdict on both revisions. The resulting packets matched the answer key. |
| T2 · Protected data | The live bank omitted the tested private fields before BRANE. The standalone suite also observed placeholder routing and inspected a separate policy preview. |
| T3 · Repeated details | The integrated bank passed the repeated-contact and name-form check. The standalone firewall **failed** one raw name variant. Its separate, locally tokenised T3b passed. |
| T4 · Untrusted instructions | The security team's recorded inputs stayed local. The letter-of-credit workflow accepts seven bank-owned message combinations. Each specialist workflow checks its own registered tasks and wordings. Human notes and source documents stay out of the model input. |
| T5 · Check unavailable (track description and CSV template) | The bank attempted one policy lookup, sent zero model requests and left the case unsealed. With no model response, the header cells in T5 are empty. [Bank outage trace](docs/evidence/firewall-outage.json) · [Client fault results](docs/evidence/brane-check-failure.csv) |
| T5 · Special-category data (participant brief) | The separate gateway check T5a recorded local routing for synthetic health information. Edge case E2 in the hand-in CSV also records local processing for indirect health context and identifies the rule in the returned headers. [Recorded T5a comparison](evidence/REPORT.md) · [Hand-in CSV, E2](submission/MAIN_Five_Tests_Template.csv) |

The original standalone run recorded **1/12** on the delivered policy and **18/20** on the first reported hardened comparison. The team's later evidence freeze repeated 20 checks three times and found **17 consistent passes, two failures and one mixed result**. Raw name coverage and preservation of ordinary trade wording failed. A benign scheduling note was sometimes refused. Those findings matter before expanding the text a model may receive. [Original measurements](https://github.com/nickdatak/OpenAIhackathon/blob/4344a6cf8b430f5fa2172a71149a1e454bf6338e/evidence/REPORT.md) · [Frozen comparison](https://github.com/nickdatak/OpenAIhackathon/blob/evidence-freeze-v1/evidence/REPORT.md) · [Integrated test worksheet](submission/MAIN_Five_Tests_Template.csv)

## Business case

**Risk comes first.** An operations head can offer staff an approved AI workflow, and the CISO and DPO can inspect what it sends. In May 2026, CB Financial Services disclosed that its subsidiary Community Bank had handled private customer information using an unauthorised AI application. The bank judged the incident material because of the volume and sensitivity of the information. Its filing gave no dollar loss. In Redwood’s live rehearsal, zero planted private fields appeared in six observed bank-to-BRANE requests. In the controlled outage, zero model requests were sent. These controls address use of the approved workflow. A bank would monitor adoption and use of other tools separately. [SEC filing, Item 1.05](https://www.sec.gov/Archives/edgar/data/1605301/000160530126000021/cbfv-20260507.htm) · [Live observation](docs/evidence/submission-live.json) · [Outage evidence](docs/evidence/firewall-outage.json)

**External estimates.** IBM’s 2025 study estimated **USD 5.56 million** as the average cost of a breach in the financial industry. Across industries, breached organisations with high use of unauthorised AI reported costs averaging **USD 670,000 more** than those with little or none. The second figure is an observed association across groups. Each benchmark describes its own population. A Redwood pilot would need a separate estimate of the loss it could prevent. [IBM financial-industry brief, p. 1](https://www.northdoor.co.uk/wp-content/uploads/2025/08/2025-Financial-CODB-Industry_Final.pdf) · [IBM study release and methodology](https://newsroom.ibm.com/2025-07-30-ibm-report-13-of-organizations-reported-breaches-of-ai-models-or-applications%2C-97-of-which-reported-lacking-proper-ai-access-controls)

**Illustrative break-even estimate.** Preventing one comparable incident could cover years of operation. For example, at an assumed **USD 100,000 per year** for the fully operated service, three years would cost **USD 300,000**. Avoiding that much loss on one incident would cover the three-year budget. A bank should replace the assumption with its own integration, monitoring and service costs, then estimate incident likelihood, adoption and the share of loss these controls could prevent. The rehearsal measured neither operating cost nor avoided incidents.

**Measured productivity and reach.** One letter-of-credit rehearsal produced **six cited desk drafts over two revisions in 29.55 seconds**, using **1,029 tokens**. Staff signatures were bound to the current revision. A separate live rehearsal carried **all 26 specialist workflows** through human sign-off. The timing covers draft preparation and validation for the trade case. Human decision time was outside the timer. [Timing and token counts](eval/utility-scorecard.csv) · [26 signed outcomes](docs/evidence/department-rehearsal-live.json)

**Manual preparation comparison.** The team reports that preparing the file manually took about twice the agent’s time. Applying that reported ratio to the recorded preparation time gives the following approximate comparison. Separate manual stopwatch readings and start/stop details were not supplied. The raw scorecard retains its original machine timings.

| Letter-of-credit preparation | Redwood, measured | Manual, inferred from team’s 2× comparison |
| --- | ---: | ---: |
| Revision 1, invoice missing | 15.852 s | About 32 s |
| Revision 2, invoice supplied | 13.702 s | About 27 s |
| Both revisions, six cited drafts | 29.55 s | About 59 s |

On the same preparation scope, this implies roughly **30 seconds less per two-revision case** or **50% less preparation time**. Staff review, approval and waiting for the invoice are separate. The capacity scenario below uses its own assumptions. [Timed API run](docs/evidence/submission-live.json) · [Independent case answer key](legal/case-answer-key.md)

**Illustrative staff-capacity estimate.** Assuming 500 cases a year, three staff minutes saved per case and EUR 60 per hour gives 25 hours, or EUR 1,500 of annual capacity for one desk. At an assumed 1,000 cases per workflow across all 27 workflows, the same assumptions yield 1,350 hours or EUR 81,000 of annual capacity before costs. A pilot should compare manual and assisted reviews of similar complexity, including time spent correcting drafts.

## Reproduce the evidence

```sh
make test
make evidence
make live-evidence
```

The first two commands run locally. The third uses the team credential to exercise both revisions through the real staff API and BRANE on a disposable database. The generated reports are under `.clearance/evidence/`. The committed evidence records the original run with its timestamp and receipt. [Evidence index](docs/evidence/README.md) · [Deployed policy definition](policy/hardened-v2.json)
