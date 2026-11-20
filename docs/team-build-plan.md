# Clearance team build plan

**Friday 20 to Saturday 21 November 2026 · Maastricht time (CET).** Ship one live case. A Dutch importer asks for a US$2m letter of credit. The agent prepares the file, Compliance requests an invoice, and the file returns to three human desks for review. A separate mandated officer decides. Operations records one simulated issuance. The [build specification](corporate-banking-hackathon-spec.md) defines the product and API. The [architecture diagram](corporate-banking-architecture.png) shows the boundaries. This plan assigns each piece to a builder and says what the next person should receive.

## First 30 minutes

| Person | Start here | Hand over by 17:00 Friday |
| --- | --- | --- |
| **Nikita Kirillov** | Sketch the approval state machine and one case screen on the same page. | To everyone: the proposed fields for case detail, three desk statuses, permitted actions, revision and packet hash. Include one response for a blocked final officer. |
| **Anastasios “Tasos” Vlachmpeis** | Work through the fixture and a single Credit Risk packet using the spec’s JSON shape. | To Nikita: a sample validated packet. To Matvei: an example model request, tool result and expected route receipt. |
| **Matvei Kandalintsev** | Get the endpoint, live policy controls, route evidence and exact five organiser checks from AI-Z. | To Tasos: the BRANE adapter interface and a fixture response. To everyone: a list of confirmed capabilities and outstanding questions, including who is following up. |
| **Ilaria Gatteschi** | Walk through the invoice hold as Coverage, Compliance and the final officer. | To Tasos: fixture facts and expected answers. To Nikita: the exact safe request, status and next owner. To Matvei: a first rule-to-evidence example. |

At 17:00, compare all four examples on the same case ID. Fix disagreements about units, role names, revision and who may resolve the hold before building separate screens or tools.

**Reuse the team's existing research.** Ilaria and Tasos can seed the evidence fields and expected desk responses from the [trade finance inventory](../research/bank-data-classification/trade-working-capital-finance.md) and the [credit risk inventory](../research/bank-data-classification/credit-counterparty-risk.md). Matvei can cross-check the proposed restricted and shareable fields against the [classification method](../research/bank-data-classification/classification-method.md). These documents supply starting examples. The actual BRANE runs supply the evidence.

## Ownership and workload

Budget **10 focused person-hours each**, an estimate assuming all four can attend the same checkpoints. Each person has **8 hours of owned work** below and **2 hours together** for contracts (30 minutes), integration and independent review (45 minutes), and rehearsal (45 minutes). Total budget is 40 person-hours. Overlapping pair time counts once against each person who attends. No one needs to be on call during the overnight break.

| Owner | One outcome they deliver | Why this assignment fits | Cross-check or backup |
| --- | --- | --- | --- |
| **Nikita** | A banker can see the hold, review the right revision and issue only after the required signatures. | Live-interface delivery, Python/SQL, algorithms and formal reasoning suit both the screen and the state rules behind it. | Matvei checks the authority rules. Tasos can drive the console from the runbook. |
| **Tasos** | One agent produces a useful, source-linked packet both with and without an invoice. | Applied ML, Python, quantitative finance and evaluation experience fit the calculations, retrieval and evidence for the agent’s claims. | Nikita integrates the packet. Ilaria checks its financial facts against an independently written answer key. |
| **Matvei** | The team can show which data reached which model, which bank controls held and what remains unverified. | AI systems security, server-side approval review and building evidence-backed software fit BRANE, access controls and the security gate. | Tasos integrates the adapter. Nikita independently checks the scope/denial behaviour. |
| **Ilaria** | Judges can inspect the cited policy, the expected financial outcome and a scorecard generated from real runs. | Business analytics, valuation, Python/R, dashboards and product research fit the fixture, policy-to-evidence mapping and measured business case. | Tasos checks the maths and scorecard. Matvei checks control mappings. Ask the AI-Z legal lead to review unresolved legal interpretations. |

The six demo identities (Coverage, Trade Finance, Credit Risk, Compliance, final officer and Operations) are bank roles. They are distinct from the four builders, who can present multiple authenticated demo sessions.

## Work tickets

Paths below are proposed destinations. A single person writes each shared module. Deliver a small callable interface or sample response early so another builder can continue in fixture mode.

### Nikita · case workflow, decisions and operator console

| Ticket | Hrs | Build and handoff | Accepted when |
| --- | ---: | --- | --- |
| N1 | 2.50 | Implement the corporate case store, assignments, revision snapshots, scoped questions/replies and atomic packet sealing in `backend/trade/` and `backend/api/trade/`. Consume Matvei’s authenticated principal and Tasos’s validated bundle. | A run can seal the current revision once. An invoice creates revision 2, preserves the outstanding hold and makes old signatures historical. |
| N2 | 2.50 | Implement desk findings, explicit hold resolution, the final mandate check, idempotency and a separate simulated Ops receipt. Reuse Tasos’s deterministic facility calculation. Own the E3/E4 workflow tests. | The owning desk clears the hold; all three required humans clear the same file; a different authorised human signs. Duplicate or concurrent commands and a restart still leave one final outcome and one receipt. |
| N3 | 2.00 | Build a compact React console: assigned queue, case with three desk rows, shared question and invoice reply, decision forms, and a filtered timeline. Use one case layout across roles. Tasos supplies the read-only review-packet component. | Six named sessions can walk one case end to end. The officer can see the blocking desk, current revision and next step. A stale response prompts a reload. |
| N4 | 1.00 | Wire seed/reset and service startup instructions, add the operator click path, and exercise the same case after a fresh launch. Hand the stage controls and instructions to Tasos once. | Another teammate starts the stack, opens the six sessions and can retrieve the simulated receipt after restarting it. |

### Tasos · agent, financial evidence and utility

| Ticket | Hrs | Build and handoff | Accepted when |
| --- | ---: | --- | --- |
| T1 | 1.50 | Turn Ilaria’s labelled scenarios into reproducible seeds in `data/trade/`. Implement integer-minor-unit exposure, currency and expiry checks; expose the calculation to Nikita. | The USD 5m line less USD 2m drawn and USD 0.5m committed leaves USD 2.5m before the request and USD 0.5m after. Missing or mismatched inputs yield an explicit unknown/blocker. |
| T2 | 2.50 | Build fixed read tools and local policy retrieval in `backend/agent/tools/`: scoped facts, facility snapshot, evidence index and approved policy passages. Each call uses Matvei’s access check; every source carries its ID/version. | The missing invoice has a named owner. Each desk receives only its permitted fields; the agent can cite an actual returned passage. |
| T3 | 2.50 | Build the **one-agent** evidence → policy → drafting workflow and typed output validator, using Matvei’s single BRANE adapter. Return a packet or typed failure for Nikita to seal. | A live run produces a useful packet. Every material figure, reference and intended audience validates. A failed run leaves the previous human history intact. |
| T4 | 1.50 | Supply `console/src/ReviewPacket.tsx` to display the packet’s facts, references and missing items. Write the clean utility evaluation in `eval/` and export actual model usage/latency to Ilaria. | Nikita can render a complete and an incomplete packet using the same component. The utility report shows expected versus observed results and a denominator. |

### Matvei · BRANE, identity and independent checks

| Ticket | Hrs | Build and handoff | Accepted when |
| --- | ---: | --- | --- |
| M1 | 2.00 | Own AI-Z integration and `backend/brane_client.py`. Provide a fixture adapter immediately, then one real request, a trace reference and a typed unavailable outcome. Publish official B1–B5 definitions when received. | Tasos can call the same interface in both modes. Receipt fields identify which observations AI-Z actually exposes. |
| M2 | 2.00 | Version the supplied baseline and hardened rules in `policy/`. Implement allowed model routes and failure handling; use the actual BRANE configuration. Own the local/cloud and outage checks E2/E5. | A permitted, restricted and blocked case each has a supported observation or an explicit evidence gap. A firewall outage halts model work. |
| M3 | 2.00 | Deliver named principals, least-privilege case/desk/document checks, bank-only name lookup and shared status projections in `backend/access/`. Wire the same checks to Nikita’s API and Tasos’s tools. Own E1. | Assigned staff see their work. Another customer’s documents and private Compliance detail are absent from unauthorised responses, including audit views. |
| M4 | 2.00 | Implement the evidence index/exporter, integrate everyone’s E-check outputs, coordinate B1–B5 and independently review N2. Give Ilaria a versioned results file for each policy. | Ten clearly identified rows show expectation, observation, policy version, run ID and verdict. Unsupported results read `unverified`; the gate is green only with ten supported hardened passes. |

### Ilaria · case truth, policy matrix and the business result

| Ticket | Hrs | Build and handoff | Accepted when |
| --- | ---: | --- | --- |
| I1 | 1.50 | Write the independent fixture answer key and desk copy in `data/trade/expected/`: incomplete file, complete file, second customer, insufficient line, expired/over-mandate, restricted attachment. Define who supplies each document and what other desks may see. | Tasos can seed cases from the facts; Nikita has usable status wording. Expected values are written independently of the code being tested. |
| I2 | 2.50 | Own the cited GDPR/EU AI Act matrix, review dates and approved demo-policy passages in `legal/` and `policy/passages/`. Join CB-01–CB-08 to actual enforcement points, test IDs and baseline/hardened evidence. | Each material claim distinguishes a bank design choice, an applicable legal provision and observed behaviour. Log legal-lead feedback or open questions. |
| I3 | 2.00 | Build `eval/business_scorecard.py` to turn Matvei’s check results, Tasos’s utility/usage and rehearsal timings into a judge-readable report. Collect a manual baseline before practising the assisted workflow. | One command regenerates counts, measured time, usage and costs/assumptions. Missing cost or timing inputs display as unknown. A reviewer can reproduce one line by hand. |
| I4 | 2.00 | Conduct an operator walkthrough against the answer key. Run the assisted timing, prepare the three-minute pitch, record the labelled backup and own the submission checklist/upload. | An observer can identify the blocker, responsible person and final authority. The release links open, the pitch fits three minutes, and the submission receipt is saved. |

## Integration appointments and evidence owners

| By (CET) | Producer → consumer | Artifact and check |
| --- | --- | --- |
| Fri 17:00 | All four → all four | Agree one fixture, six principal aliases, sealed packet shape, required findings and evidence row. Nikita records the contract; Matvei records unknowns for AI-Z. |
| Fri 18:30 | Ilaria → Tasos/Nikita · Matvei → Tasos/Nikita | Answer key and safe Compliance wording; callable fixture adapter and authenticated-principal example. Nikita and Tasos return role-filtered case and packet JSON. |
| Fri 21:30 | Tasos + Matvei → Nikita · Nikita → Ilaria | One real BRANE trace and evidence-linked packet if access is available. Case UI can render the fixture and current review state either way. Ilaria records the manual comparison and starts the report. |
| Fri 23:15 | All four → integration build | Walk the invoice hold → amendment → reseal → three fresh clears → distinct final officer → simulated receipt. Reopen after restart. Record live and fixture results separately. |
| Sat 07:45 | Matvei + Tasos + Nikita → Ilaria | Ten-check index with verdicts, clean utility, timing/usage, reproducible fixture, workflow audit, receipt and runnable instructions. Ilaria links these to the policy matrix and scorecard. |
| Sat 09:15 target | Ilaria → organisers | Submit the frozen revision, verified links, evidence, pitch and backup. Nikita is upload backup; record organiser confirmation. Official deadline **10:30 CET**. |

**Check allocation.** Matvei owns E1 (case isolation), E2 (local/cloud boundary) and E5 (outage). Nikita owns E3 (human hold) and E4 (revision/concurrent finalisation). Tasos supplies model traces and utility; Ilaria supplies labelled scenarios and reads the evidence as a judge. For the stage case, missing invoice means Trade also waits. For the E3 isolation check use a *complete* file with a separate unresolved Compliance hold, so Trade and Credit can validly clear while final approval still stays blocked.

Matvei obtains the official five check definitions. Reserve execution slots B1 and B2 for Matvei, B3 for Tasos, B4 for Nikita and B5 for Ilaria paired with Matvei. Move a slot to the appropriate owner once its actual test is known and swap a slot back to preserve workload. Matvei consolidates results. Each implementer has a second reader: Matvei reviews Nikita’s signatures, Nikita reviews Matvei’s role projections, Ilaria checks Tasos’s financial outputs, and Tasos reruns Ilaria’s scorecard. Measure the supplied baseline and hardened policy independently.

## Working hours and contingencies

| Maastricht work block | Focus | Person-hours each |
| --- | --- | ---: |
| Fri 16:30–18:30 | Shared 30-minute contract session, then four parallel starts. | 2.00 |
| Fri 19:00–21:30 | Build desk packet, access controls, backend transitions and policy inputs. Run the first live integration as early as the endpoint allows. | 2.50 |
| Fri 21:45–Sat 00:15 | Integrate the stage case; use 22:30–23:15 for the joint run and independent checks. Write down remaining failures before the overnight break. | 2.50 |
| Sat 05:45–07:45 | Fix blockers, run both policy configurations, regenerate reports and perform a clean checkout. Aim to freeze at 08:00. | 2.00 |
| Sat 08:15–09:15 | Shared 45-minute timed rehearsal and backup, then final packaging and submission. | 1.00 |

If live access is delayed at 18:30, Matvei continues with AI-Z while the other three use the labelled fixture adapter. If the console is the bottleneck at 21:30, Tasos takes the read-only audit view using Nikita’s API; Nikita takes the clean utility rerun against Ilaria’s answer key. If collecting route evidence is slow, Ilaria takes over assembling the ten-row index from Matvei’s redacted exports; Matvei takes over checking her rule-to-enforcement joins. Swap at most one ticket-hour per person at a checkpoint and record the new owner.

Cut the optional FX quote, graph store, extra departments and visual polish first. Protect the live BRANE path, the three desk clearances, separate final decision, evidence gate and legal matrix. If a result is unverified at freeze, report it accurately. Keep 09:15–10:30 available for a failed upload or an organiser-requested correction.

## Stage roles

Ilaria opens with the importer’s problem (0:00–0:20). Tasos narrates the agent and source-backed USD 500k remaining headroom (0:20–0:55). Nikita drives the hold, invoice, renewed signatures, final decision and one simulated receipt (0:55–2:05). Matvei shows an actual baseline/hardened observation and gate results (2:05–2:40). Ilaria closes with the measured handoff benefit and the buyer (2:40–3:00).

Use the same task boundaries for manual and assisted timing. Mark recorded footage, synthetic evidence and simulated issuance on screen. If two live runs exceed the pitch window, start with a clearly labelled prior revision-1 packet and run revision 2 live. Each demo-stage signature is supplied by the authenticated human role for the file under review.
