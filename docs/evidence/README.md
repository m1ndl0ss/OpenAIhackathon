# Evidence for the submission

| Open this file | What was observed |
| --- | --- |
| [Integrated live case](submission-live.json) | Two revisions, three departments, the real OpenAI model through BRANE, per-call route and digest, citation checks, three current signatures, the officer decision and one simulated receipt. Six distinct scripted staff identities used the API. |
| [Specialist live rehearsal](department-rehearsal-live.json) | One case per specialist desk through approval. BRANE reported 57 cloud and 12 local-model calls. Three restricted desks recorded zero model calls. |
| [Specialist routing dashboard](specialist-workflow.jpg) | Payments & Cash servicing a returned payment during an actual live run. |
| [Merged BRANE client checks](brane-check-failure.csv) | Five faults repeated three times returned zero answer text. Three healthy controls returned a verified response. The observer checked each destination and port from the client process. |
| [Network-denied outage](firewall-outage.json) | T5 in its official firewall-unavailable meaning. An independent Python audit hook denied DNS and IP socket operations. The bank attempted its policy lookup, submitted zero model requests and left the case unsealed. |
| [Submission test worksheet](submission-tests.csv) | The five official scenarios and the team's five edge cases. Each row identifies the application, gateway or controlled-outage evidence. |
| [Submission policy matrix](submission-policy-matrix.csv) | Eleven rules from Ilaria's legal worksheet with observed gateway behaviour and application controls. The legal-source column matches her source sheet. |
| [Timed backup walkthrough](live-walkthrough.gif) | Seven Redwood browser captures from a separate live case, from desk entry through simulated issuance. |
| [Fixture hold and retry checks](workflow-fixture.csv) | A compliance hold prevents approval. A stale revision fails. Concurrent requests and application restart preserve one receipt. |
| [Fixture utility](agent-utility-fixture.json) | Two offline scenarios scored against the case answer key. |

The security team captured its own baseline, hardened gateway results and ten-row worksheet. The raw-firewall T3 and T3c failures remain visible there. [Baseline](../../evidence/baseline_run.csv) · [Gateway results](../../evidence/REPORT.md) · [Security worksheet](../../evidence/MAIN_Five_Tests_Template.csv)

Ilaria revised the rationale and legal sources for CB-04 and CB-10. The submission and gateway matrices include her revisions. The original worksheet is available for comparison. [Current cited source](../../evidence/clearance_policy_matrix.source.csv) · [Gateway matrix](../../evidence/clearance_policy_matrix.csv) · [Original worksheet](policy-matrix.csv)

**Reproduce locally.** Run `make setup`, `make test` and `make evidence`. The local commands exercise fixtures and the outage in a disposable environment. Set the team credential as described in the run guide and use `make live-evidence` for a new live case. Reports are written under `.clearance/evidence/`. Only the reviewed artifacts above are used in the submission. [Demo and business case](../../SUBMISSION.md)
