# Clearance · Who builds what

## 1. Run the letter-of-credit workflow and finish the challenge demo

The local console supports a USD 2 million import letter of credit in fixture mode. Start the app with `make setup` and `make run`. In the local console choose **Coverage** and open `LC-001`. The walkthrough takes you from the missing invoice to a single simulated receipt. [Run and sign in](../README.md#run-from-a-fresh-clone) · [Role-by-role walkthrough](../README.md#walk-the-case)

Trade Finance, Credit Risk and Compliance sign the current file. A separate mandated officer decides, and Operations records simulated issuance. The team still needs to connect and verify the live BRANE agent for the challenge. [Build specification](corporate-banking-hackathon-spec.md) · [Architecture diagram](corporate-banking-architecture.png)

### Matvei Kandalintsev — BRANE setup and security

- **Connect BRANE.** Configure the team department, credentials, local model route and permitted cloud route using the [BRANE starter kit](MAIN_Participant_Starter_Kit/starter-kit/README.md). Deliver one adapter in `backend/brane_client.py` with live and clearly labelled fixture modes. Give Tasos callable examples of success, refusal and firewall unavailability.
- **Configure the data rules.** Save the supplied baseline and hardened policy versions. Enforce which fields can pass, which require masking, which stay local and which requests are refused. Route model-bound tool results through the same firewall. A BRANE outage must stop model work.
- **Build the access controls.** Supply a shared permission check for case, desk, document and tool access, plus a bank-only lookup for permitted names. Nikita calls it from the API; Tasos calls it from the tools. Restricted Compliance details stay with authorised staff.
- **Verify the security boundary.** Run the five official checks (T1–T5) from [AI-Z’s evidence template](MAIN_Participant_Starter_Kit/MAIN_Five_Tests_Template.csv) under both policies alongside E1 (case isolation), E2 (local/cloud boundary) and E5 (outage). Give Ilaria redacted results with the policy version, verdict, trace reference and any gap in what AI-Z exposes.

### Nikita Kirillov — case backend, human approvals and console

- **Build the corporate case API and database.** Implement the six named human sessions, case assignments, evidence versions, desk questions and replies, and role-filtered audit history. Apply Matvei’s access checks to every case view and action.
- **Build the approval workflow.** Seal Tasos’s validated packet. A new invoice creates a new revision and reopens review. Only the owning desk can clear its hold. Require three distinct current-version desk signatures, a separate final officer acting within mandate, and a separate Operations action for the simulated receipt.
- **Build the staff console.** Deliver the assigned queue, case screen, three desk findings, invoice request/reply, final decision form and Operations receipt. Use Ilaria’s approved wording and Tasos’s source-linked packet component. Show the blocking desk and permitted next action.
- **Make it runnable and test it.** Provide startup/reset commands and synthetic logins. Deliver E3 (an open Compliance hold blocks approval) and E4 (stale revisions and concurrent retries cannot duplicate a decision or receipt). Give Ilaria the test results and a reproducible demo case.

### Anastasios “Tasos” Vlachmpeis — agent, banking calculations and review packets

- **Build the synthetic data and credit calculation.** Turn Ilaria’s answer key into reproducible fixtures. Compute facility headroom in code: USD 5m limit less USD 2m drawn and USD 0.5m committed leaves USD 2.5m available. The proposed USD 2m letter leaves **USD 0.5m**. Return an explicit blocker for missing, expired or incompatible inputs.
- **Build the agent’s read-only tools.** Implement scoped access to case facts, facility balances, evidence references and approved policy passages. Apply Matvei’s permission checks and preserve the source ID and version for every material fact.
- **Build one agent with three tasks:** gather evidence, look up policy, and draft a packet for each desk. Use Matvei’s BRANE adapter for every model call. Validate numbers, citations, audience and missing-document requests before handing a packet to Nikita.
- **Build the packet display and utility evaluation.** Deliver the read-only React component for facts, sources and outstanding questions. Compare runs against Ilaria’s independent answer key and export observed results, model usage and missing measurements for the scorecard.

### Ilaria Gatteschi — case requirements, policy matrix and submission

- **Write the independent case answer key.** Define expected amounts, desk outcomes, safe questions and who supplies each missing item. Include a missing-invoice case and a complete file with a separate Compliance hold, so Nikita can test whether that hold alone blocks approval.
- **Build the cited policy matrix and policy passages.** Map each data class and action to the bank rule, legal source, enforcement point and test. Distinguish the bank’s human-signature policy from legal requirements. Give Tasos versioned passages for retrieval.
- **Build the evidence report and business scorecard.** Combine Matvei’s eight check results and Nikita’s two in the official evidence CSV. Use the [policy matrix template](MAIN_Participant_Starter_Kit/MAIN_Policy_Matrix_Template.csv) for the cited rules. Show baseline and hardened observations side by side. Use Tasos’s evaluation and a manual comparison to report utility, operational benefit and cost. Keep failed and unverified results visible.
- **Build the submission package.** Deliver the judge-facing demo script, labelled backup recording, evidence links and business case. The walkthrough must show the hold, invoice amendment, renewed signatures, separate final decision and single simulated receipt.

## 2. Support multiple banking workflows

**Planned scope.** Give staff one assigned queue across the existing issuance workflow and all 26 workflows in the bank research catalogue. The catalogue covers six corporate banking workflows, five in markets and securities, ten in risk and control, and five in group functions. It includes activities such as credit-pack review, FX handover, treasury liquidity review and internal audit. Each entry defines a specific job a person needs to finish. For example, issuing a letter of credit and reviewing documents subsequently presented under it are two different jobs. [Full workflow catalogue](../research/bank-data-classification/README.md)

### Build the first three additional workflows

| Workflow | What staff should be able to do | Human decision and visible result |
| --- | --- | --- |
| [KYC missing-document follow-up](../research/bank-data-classification/kyc.md) | An onboarding analyst sees which evidence is missing and receives a draft request. Identity documents and the actual recipient stay inside the bank. | The analyst checks the wording and recipient, and records whether to request evidence or mark the file ready for review. |
| [Payment exception triage](../research/bank-data-classification/payments-cash-correspondent.md) | A payments analyst matches a returned transfer to its original record and reviews a draft internal handover. | The analyst confirms the match or refers the exception. The case history records the disposition. Any resubmission is a separate authorised action. |
| [Restricted AML investigation handover](../research/bank-data-classification/aml-sanctions-fraud.md) | An assigned investigator prepares a handover within the restricted case. Its records, metadata and reporting status stay local throughout. | An authorised investigator accepts or refers the handover. The check for this case must show zero external requests. A generic training checklist uses a separate fixture. |

### Build the shared pieces and cover the catalogue

| Owner | Deliverable |
| --- | --- |
| **Nikita** | Give every case a workflow ID and definition version. Load the assigned desks, evidence requirements, permitted decisions, final human owner and completion action for that version. Build the workflow picker, filtered queue and case-specific forms. Keep existing letter-of-credit cases and receipts readable. |
| **Matvei** | Configure each workflow's BRANE routes, field rules and case-level blocks. Enforce access by workflow, case, desk, document and tool. Verify that a user assigned to two workflows can see only the evidence permitted in each. Capture redacted route or zero-egress evidence. |
| **Tasos** | Add synthetic inputs, read-only tools, deterministic checks and source-linked packets for each workflow. Use the selected definition to build the allowed model input. Give local-only cases an internal handover path. |
| **Ilaria** | Maintain a coverage table with one row per catalogue entry, its human owner, expected outcome, fixture, implementation status and evidence link. Define the required desk sign-offs and final decision for each workflow, including whether completion creates an internal note, referral or simulated receipt. |

**When a workflow counts as supported.** An assigned person can open a seeded case, inspect the evidence their desk is entitled to see, complete its human approvals and recover the recorded outcome after a refresh. An unassigned user is denied. Missing evidence, a required desk hold or a stale signature blocks completion. For each of the 26 profiles, run its five research scenarios and record the observed result and evidence. Track fixture verification and live BRANE verification separately. Keep the existing letter-of-credit walkthrough and E3/E4 passing as each workflow is added. [Research test definitions](../research/bank-data-classification/classification-method.md) · [Current workflow evidence](evidence/README.md)
