# Workflow evidence

All records use synthetic cases. The live runs used separate scripted staff identities through the staff API. Request observations cover what the application sent to BRANE. Downstream routing and usage come from the gateway’s response headers.

| Record | Observation |
| --- | --- |
| [Letter of credit](submission-live.json) | The first revision identifies a missing invoice and USD 500,000 in remaining capacity. The second cites the invoice, collects three current signatures and ends with one simulated receipt. Each of the six model calls has a policy digest, route and usage record. |
| [Preparation times](preparation-times.csv) | The two revisions took 15.852 and 13.702 seconds to draft and validate. Rows for the same revision share that revision’s timing. |
| [Repeat run](readiness-live.json) | Both revisions completed again. Their six drafts passed the source checks in 47.63 seconds of preparation time. |
| [Specialist desks](department-rehearsal-live.json) | One case per desk reached a signed decision. The gateway reported 57 cloud calls and 12 local-model calls. Three of the 26 workflows completed entirely in bank code. |
| [Unavailable firewall](firewall-outage.json) | With DNS and IP sockets denied, the application attempted one policy lookup, made zero model requests and left the case unsealed. |
| [Client fault results](brane-check-failure.csv) | Five faults repeated three times returned no answer text. Three healthy controls returned verified responses. |
| [Approval and retry checks](workflow-fixture.csv) | In local fixture mode an open hold and a stale revision each blocked approval. Concurrent retries and a restart preserved a single issuance receipt. |

The [test protocol](../../submission/MAIN_Five_Tests_Template.csv) identifies the observation behind each test. The [gateway report](../../evidence/REPORT.md) documents the separate trials on raw document text, including missed and excessive masking. The [policy matrix](../../submission/MAIN_Policy_Matrix_Template.csv) links the controls to their legal sources.
