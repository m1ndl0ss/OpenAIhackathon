# How Redwood calls BRANE

The bank computes figures, selects evidence and checks staff permissions before a model call. The model receives the desk task, the next-step code and permitted wordings. The bank attaches figures and citations to the selected wording and checks the result before a human can sign it. Three restricted workflows complete their drafting tasks in bank code. [Draft validation](../backend/agent/runtime.py) · [Department workflows](../data/workflows/departments-v1.json)

## Before each call

The adapter accepts only registered messages for the requested desk task and an empty tool schema. It reads the policy from the assigned HTTPS endpoint, compares the digest with the checked-in policy and checks whether any semantic rule is disabled. A policy mismatch or unavailable policy stops the call. The client disables redirects. [Staff adapter](../backend/brane_client.py) · [Policy configuration](../policy/README.md)

## Outcomes

| Outcome | Evidence the adapter requires | Effect on the case |
| --- | --- | --- |
| Direct | HTTP 200, cloud route, allow action and redaction flag set to false | The bank validates the draft. |
| Pseudonymised | HTTP 200, cloud route, placeholder action, redaction flag set to true and recorded placeholder classes | The bank validates the draft and records the reported classes. |
| Local | HTTP 200, local route and action, and a resolved local model | The bank validates the draft and records the reported route. |
| Blocked | HTTP 422 with the refused route and refuse action | The file stays unsealed. |
| Unavailable | Transport failure, inconsistent verdict or a missing required observation | The file stays unsealed. One transient failure may be retried within the agent’s existing call and time budgets. |

The adapter records HTTP status, the policy digest, timestamp, reported route and available routing headers. The agent validates a successful response against that task’s permitted wording before it can seal the packet. Staff approvals and simulated issuance are recorded separately for the current revision. [Outcome classifier](../scripts/brane_client.py) · [Recorded case and approvals](evidence/submission-live.json)

## What the measurements cover

For six live drafts, the bank observed zero matches for its planted private fields in outbound requests. The route and applied rules after that point come from BRANE’s headers. With network access denied, the bank attempted only the policy lookup. The client also suppressed every response in 15 controlled fault runs and accepted all three healthy controls. The network observer covers the client process. [Live case](evidence/submission-live.json) · [Outage trace](evidence/firewall-outage.json) · [Client fault results](evidence/brane-check-failure.csv)

In separate free-text tests the gateway’s preview missed a name variant and altered ordinary trade terms. Those tests describe risks of expanding the information a model receives. [Gateway findings](../evidence/REPORT.md)
