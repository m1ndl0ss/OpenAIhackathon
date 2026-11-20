# Letter-of-credit case answer key

Ilaria Gatteschi, 20 November 2026. This worksheet gives the expected results for two synthetic cases. Each case has its own facility snapshot. The officer’s mandate, desk sign-off rules and invoice requirement are synthetic bank policy. [Case fixture](../data/trade/demo.json) · [Policy matrix](../submission/MAIN_Policy_Matrix_Template.csv)

## Credit capacity and mandate

| Item | Expected result in both cases |
| --- | --- |
| Facility | USD 5,000,000 limit, USD 2,000,000 drawn and USD 500,000 already committed |
| Headroom before issuance | USD 2,500,000 (250,000,000 cents) |
| Requested instrument | USD 2,000,000 import letter of credit for machine parts |
| Headroom after proposed issuance | USD 500,000 (50,000,000 cents), within limit |
| Currency and expiry | Both records use USD. The instrument expires on 31 January 2027, before the facility expires on 31 March 2027. |
| Mandate | The separate final officer may decide on an instrument up to USD 3,000,000. |

## LC-001 with a missing invoice

| Step | Expected finding or action |
| --- | --- |
| First analysis | Trade Finance and Compliance identify the missing supplier invoice. Coverage owns the request. Credit Risk calculates the figures above using `FAC-USD-01@1`. |
| Revision 1 review | Credit Risk clears. Compliance places a `DOCUMENT_REQUIRED` hold and requests the invoice from Coverage. Trade Finance stays pending. The officer cannot approve, and Operations has no receipt. |
| Evidence arrives | Coverage attaches the USD 2,000,000 pro forma invoice for the synthetic supplier, `ORG_DEMO_02`. The file advances to revision 2. Prior clearances become historical and the Compliance hold stays open. |
| Second analysis | Trade Finance and Compliance cite `DOC-INV-01@1`. Neither identifies a missing invoice. Credit Risk reaches the same headroom figure. |
| Revision 2 review | Trade Finance and Credit Risk sign the current file. Compliance selects its open hold, cites the reviewed invoice and signs with `CHECKS_COMPLETE`. The case becomes `ready_for_decision`. |
| Decision and issuance | The mandated officer records an approval with a reason. A separate Operations user records exactly one simulated receipt for revision 2. Retrying issuance returns the same receipt. |

The three desk signatures can arrive in any order. Each event records its actor, UTC time and revision. The live case record includes the source checks, a rejected attempt to approve a held file, a rejected stale decision and the final receipt. [Live case record](../docs/evidence/submission-live.json) · [Packet checks](../tools/agent_utility.py)

## LC-002 with a complete invoice

Trade Finance and Credit Risk can clear the file. A Compliance reviewer can still place a `MANUAL_REVIEW` hold after reading the restricted screening record. Other desks see “Waiting for Compliance.” The final officer cannot approve while the hold is open. Only Compliance can resolve it. With all three current signatures, the officer may record the decision and Operations may simulate issuance. [Workflow tests](../tests/test_trade_workflow.py)

## Model input and bank-side evidence

| Data or event | Expected handling | Policy rule |
| --- | --- | --- |
| Desk drafting request | Send only the registered desk, next-step code and two approved wordings through BRANE. Accept a response only if it selects a permitted wording. | CB-01, CB-02 |
| Identifiers, contact details, amounts, limits, pricing and raw invoice | Keep these inside the bank. Bank code calculates headroom and attaches the permitted figures and references to the draft. | CB-02, CB-05, CB-09 |
| Restricted screening record | Only Compliance can read it. Other desks receive the status of the hold. | CB-03, CB-05 |
| BRANE policy check unavailable | Stop before sending a model request. Keep the file pending without a new sealed packet. | CB-07 |
| Desk clearances, final decision and receipt | Bind each signature to the current revision. The officer’s decision unlocks simulated issuance for Operations. | CB-06, CB-08 |
