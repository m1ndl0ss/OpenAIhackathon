# Evidence for the submission

| Open this file | What was observed |
| --- | --- |
| [Integrated live case](submission-live.json) | Two revisions, three departments, the real OpenAI model through BRANE, per-call route and digest, citation checks, three current signatures, the officer decision and one simulated receipt. Six distinct scripted staff identities used the API. |
| [Network-denied outage](firewall-outage.json) | T5 in its official firewall-unavailable meaning. An independent Python audit hook denied DNS and IP socket operations. The bank attempted its policy lookup, submitted zero model requests and left the case unsealed. |
| [Submission test worksheet](submission-tests.csv) | The five official scenarios and the team's five edge cases. Each row identifies the application, gateway or controlled-outage evidence. |
| [Submission policy matrix](submission-policy-matrix.csv) | Eleven rules from Ilaria's legal worksheet with observed gateway behaviour and application controls. The legal-source column matches her source sheet. |
| [Timed backup walkthrough](live-walkthrough.gif) | Seven captioned browser captures of a second live case from desk entry to simulated issuance. |
| [Fixture hold and retry checks](workflow-fixture.csv) | A compliance hold prevents approval. A stale revision fails. Concurrent requests and application restart preserve one receipt. |
| [Fixture utility](agent-utility-fixture.json) | Two offline scenarios scored against the case answer key. |

The security team captured its own [baseline](../../evidence/baseline_run.csv), [hardened gateway results](../../evidence/REPORT.md) and [original ten-row worksheet](../../evidence/MAIN_Five_Tests_Template.csv). The raw-firewall T3 and T3c failures remain visible there. The [original cited matrix](policy-matrix.csv) and [gateway-layer matrix](../../evidence/clearance_policy_matrix.csv) preserve the earlier workstream snapshots.

**Reproduce locally.** Run `make setup`, `make test` and `make evidence`. The local commands exercise fixtures and the outage in a disposable environment. Set the team credential as described in the run guide and use `make live-evidence` for a new live case. Reports are written under `.clearance/evidence/`. Only the reviewed artifacts above are used in the submission. [Demo and business case](../../SUBMISSION.md)
