# BRANE policy results

Redwood recorded two kinds of evidence on synthetic banking cases. The staff application logged the fields it sent to BRANE, its accepted drafts and the subsequent human approvals. The gateway tests sent synthetic document text separately and recorded BRANE’s response headers. A separate policy preview exposed the substitutions BRANE predicted. Downstream model traffic was outside the bank’s observation. [Application run](../docs/evidence/submission-live.json) · [Completed checks](../submission/MAIN_Five_Tests_Template.csv)

## Policy comparison

| Policy | Recorded result | Change observed |
| --- | --- | --- |
| Delivered baseline | 1 of 12 checks passed | The public control completed. The other 11 checks failed under a policy that allowed all 25 data categories. [Baseline results](baseline_run.csv) · [Policy](../policy/baseline-open.json) |
| Hardened v1 | 13 of 16 distinct checks passed | Repeated-name protection, explicit health information and indirect health information still failed. The consolidated file retains all 49 original rows and their run timestamps. [Runs](hardened-v1-runs.csv) · [Policy](../policy/hardened-v1.json) |
| Hardened v2 | 18 of 20 checks passed in each of three initial runs | The added health-context rule routed both health cases locally. Name handling and preservation of trade wording still failed. [First run](redwood-hardened-v2_20261120T165427Z.csv) · [Second run](redwood-hardened-v2_20261120T165652Z.csv) · [Third run](redwood-hardened-v2_20261120T165926Z.csv) · [Policy](../policy/hardened-v2.json) |

A later repeat of the 20 v2 checks found 17 consistent passes, the same two failures and one mixed result. BRANE routed a benign scheduling note locally twice and refused it once on identical input. These observations limit how reliably staff can obtain a draft for that case. [Later comparison](https://github.com/nickdatak/OpenAIhackathon/blob/5caaa23504c74025181b5f34b142113c4fc34ddb/evidence/REPORT.md)

## What the staff workflow protects

| Scenario | Observation |
| --- | --- |
| Permitted request (T1) | Credit Risk completed both revisions through the cloud route. Both drafts cited the bank’s sources and reported USD 500,000 of remaining facility headroom. [Signed case](../docs/evidence/submission-live.json) |
| Protected data (T2) | The bank observed zero matches for the planted private fields in six outgoing requests. The standalone gateway returned cloud redaction headers for identifiers in its separate synthetic text test. [Outbound observations](../docs/evidence/submission-live.json) · [Gateway results](redwood-hardened-v2_20261120T165926Z.csv) |
| Repeated details (T3) | The raw gateway preview retained one form of a synthetic surname. Local tokenisation protected the case’s known aliases in T3b. In the staff workflow, the notes containing the repeated contact information stayed in the bank. [Gateway results](redwood-hardened-v2_20261120T165926Z.csv) · [Staff workflow](../docs/evidence/submission-live.json) |
| Untrusted content (T4) | All three synthetic invoice variants routed locally in each initial v2 run. The staff adapter accepts only registered messages for each desk task. [Gateway results](redwood-hardened-v2_20261120T165926Z.csv) · [Adapter](../docs/brane_adapter_contract.md) |
| Firewall unavailable (T5) | With socket access denied, the bank attempted one policy lookup, submitted zero model requests and left the case unsealed. [Bank outage trace](../docs/evidence/firewall-outage.json) |

The gateway tests also distinguish sensitive content from an unavailable business check. T5a and E2 routed synthetic health context to the local model. T5b returned HTTP 422 when asked to proceed with an unverified screening result. The firewall itself was reachable in all three cases. [Gateway results](redwood-hardened-v2_20261120T165926Z.csv)

## Outage and response validation

The client faced five faults including a missing routing verdict on an otherwise successful response. In the governed client’s 15 fault runs, zero answer characters reached the caller. Three healthy controls returned usable answers. A socket audit hook recorded the DNS and connection attempts made by that process. The raw transport exposed 121 characters from the response with the missing verdict. The integrated client repeated the five faults and healthy controls with port-specific observation and reproduced all 18 expected outcomes. [Governed client](redwood-A5-check-failure_20261120T175417Z.csv) · [Raw transport](redwood-A5-check-failure_20261120T175012Z.csv) · [Integrated client](../docs/evidence/brane-check-failure.csv)

## Limits on broader use

- **Name consistency.** One person could receive different placeholders across spellings, and a surname-first form remained visible in the gateway preview. The six bank drafts used registered wording and contained none of the planted contact fields. Free-text drafting would expose a wider range of inputs. [T3 and T3b](redwood-hardened-v2_20261120T165926Z.csv) · [Recorded bank requests](../docs/evidence/submission-live.json)
- **Meaning after masking.** In T3c the gateway preview replaced ordinary terms including “expiry on” and “Beneficiary.” A correct routing decision alone could therefore leave the model with an inaccurate commercial statement. [T3c result](redwood-hardened-v2_20261120T165926Z.csv)
- **Policy granularity.** Organisation-name handling applies across a department. The same rule can hide a public counterparty name a reviewer needs for a lookup. The bank also keeps free-text commercial terms in its own system and enforces case and desk permissions itself. [Policy decisions and gaps](../submission/MAIN_Policy_Matrix_Template.csv)
- **Attribution.** A local-route cause in E3 differed from the screening and data-category triggers. The adapter records those fields separately. The bank can inspect its own requests, while the route beyond BRANE comes from gateway headers. [E3 result](redwood-hardened-v2_20261120T165926Z.csv) · [Adapter observations](../backend/brane_client.py)

The policy matrix links each control to its legal basis, implementation and supporting observations. The original legal worksheet supplies the reviewed rationale and citations for each of the eleven controls. [Completed policy matrix](../submission/MAIN_Policy_Matrix_Template.csv) · [Reviewed legal source](clearance_policy_matrix.source.csv)
