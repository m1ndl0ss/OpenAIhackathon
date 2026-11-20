# Clearance · Who builds what

Ship one corporate letter-of-credit case. The agent prepares the evidence. Trade Finance, Credit Risk and Compliance each sign the current file. A separate mandated officer decides, and Operations records one simulated issuance. [Build specification](corporate-banking-hackathon-spec.md) · [Architecture diagram](corporate-banking-architecture.png)

## Matvei Kandalintsev — BRANE setup and security

- **Connect BRANE.** Configure the team department, credentials, local model route and permitted cloud route using the [BRANE starter kit](MAIN_Participant_Starter_Kit/starter-kit/README.md). Deliver one adapter in `backend/brane_client.py` with live and clearly labelled fixture modes. Give Tasos callable examples of success, refusal and firewall unavailability.
- **Configure the data rules.** Save the supplied baseline and hardened policy versions. Enforce which fields can pass, which require masking, which stay local and which requests are refused. Route model-bound tool results through the same firewall. A BRANE outage must stop model work.
- **Build the access controls.** Supply a shared permission check for case, desk, document and tool access, plus a bank-only lookup for permitted names. Nikita calls it from the API; Tasos calls it from the tools. Restricted Compliance details stay with authorised staff.
- **Verify the security boundary.** Run the five official checks (T1–T5) from [AI-Z’s evidence template](MAIN_Participant_Starter_Kit/MAIN_Five_Tests_Template.csv) under both policies alongside E1 (case isolation), E2 (local/cloud boundary) and E5 (outage). Give Ilaria redacted results with the policy version, verdict, trace reference and any gap in what AI-Z exposes.

## Nikita Kirillov — case backend, human approvals and console

- **Build the corporate case API and database.** Implement the six named human sessions, case assignments, evidence versions, desk questions and replies, and role-filtered audit history. Apply Matvei’s access checks to every case view and action.
- **Build the approval workflow.** Seal Tasos’s validated packet. A new invoice creates a new revision and reopens review. Only the owning desk can clear its hold. Require three distinct current-version desk signatures, a separate final officer acting within mandate, and a separate Operations action for the simulated receipt.
- **Build the staff console.** Deliver the assigned queue, case screen, three desk findings, invoice request/reply, final decision form and Operations receipt. Use Ilaria’s approved wording and Tasos’s source-linked packet component. Show the blocking desk and permitted next action.
- **Make it runnable and test it.** Provide startup/reset commands and synthetic logins. Deliver E3 (an open Compliance hold blocks approval) and E4 (stale revisions and concurrent retries cannot duplicate a decision or receipt). Give Ilaria the test results and a reproducible demo case.

## Anastasios “Tasos” Vlachmpeis — agent, banking calculations and review packets

- **Build the synthetic data and credit calculation.** Turn Ilaria’s answer key into reproducible fixtures. Compute facility headroom in code: USD 5m limit less USD 2m drawn and USD 0.5m committed leaves USD 2.5m available. The proposed USD 2m letter leaves **USD 0.5m**. Return an explicit blocker for missing, expired or incompatible inputs.
- **Build the agent’s read-only tools.** Implement scoped access to case facts, facility balances, evidence references and approved policy passages. Apply Matvei’s permission checks and preserve the source ID and version for every material fact.
- **Build one agent with three tasks:** gather evidence, look up policy, and draft a packet for each desk. Use Matvei’s BRANE adapter for every model call. Validate numbers, citations, audience and missing-document requests before handing a packet to Nikita.
- **Build the packet display and utility evaluation.** Deliver the read-only React component for facts, sources and outstanding questions. Compare runs against Ilaria’s independent answer key and export observed results, model usage and missing measurements for the scorecard.

## Ilaria Gatteschi — case requirements, policy matrix and submission

- **Write the independent case answer key.** Define expected amounts, desk outcomes, safe questions and who supplies each missing item. Include a missing-invoice case and a complete file with a separate Compliance hold, so Nikita can test whether that hold alone blocks approval.
- **Build the cited policy matrix and policy passages.** Map each data class and action to the bank rule, legal source, enforcement point and test. Distinguish the bank’s human-signature policy from legal requirements. Give Tasos versioned passages for retrieval.
- **Build the evidence report and business scorecard.** Combine Matvei’s eight check results and Nikita’s two in the official evidence CSV. Use the [policy matrix template](MAIN_Participant_Starter_Kit/MAIN_Policy_Matrix_Template.csv) for the cited rules. Show baseline and hardened observations side by side. Use Tasos’s evaluation and a manual comparison to report utility, operational benefit and cost. Keep failed and unverified results visible.
- **Build the submission package.** Deliver the judge-facing demo script, labelled backup recording, evidence links and business case. The walkthrough must show the hold, invoice amendment, renewed signatures, separate final decision and single simulated receipt.
