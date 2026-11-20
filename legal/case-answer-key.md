# Case acceptance worksheet

Ilaria owns this independent answer key and the approved wording for desk decisions. The starter expectations come from the stage scenario. Record any signed-off change here before using it to score agent output.

| Case and condition | Expected finding | Responsible staff |
| --- | --- | --- |
| LC-001, initial file | The supplier invoice is missing. The shareable request asks Coverage to supply it. Pending review permits no issuance. | Compliance requests, Coverage supplies |
| LC-001, credit capacity | USD 5m limit less USD 2m drawn and USD 0.5m committed gives USD 2.5m before the proposal. The USD 2m instrument leaves USD 0.5m. | Credit Risk |
| LC-001, invoice arrives | The new revision requires all three desks to sign again. The old Compliance hold remains until Compliance explicitly resolves it using the invoice. | All three desks |
| LC-002, complete file with a Compliance hold | Trade and Credit can clear. Compliance alone can resolve its hold. The final officer cannot approve while it is open. | Compliance |
| Approved case | A separate Operations human can produce exactly one simulated receipt for the approved file. | Operations |

## Detailed expected results

Prepared by Ilaria Gatteschi, 20 November 2026. Based on `docs/corporate-banking-hackathon-spec.md` and checked against the current workflow code. All data is synthetic.

Units: money in integer minor units (USD cents). Fixture clock: 20 Nov 2026 14:00 UTC.

---

## 1. Shared facts (case A and B)

| Item | Value | Minor units |
|---|---|---|
| Facility `FAC-USD-01` limit | USD 5,000,000 | 500000000 |
| Drawn | USD 2,000,000 | 200000000 |
| Already committed | USD 500,000 | 50000000 |
| **Headroom before issue** | 5,000,000 − 2,000,000 − 500,000 = **USD 2,500,000** | 250000000 |
| Requested LC | USD 2,000,000 | 200000000 |
| **Headroom after issue** | 2,500,000 − 2,000,000 = **USD 500,000** | 50000000 |
| Credit result | `within_limit` | |
| Currency check | request USD = facility USD, no FX needed | |
| Expiry check | LC expiry 2027-01-31 ≤ facility expiry 2027-03-31: OK | |
| Mandate check | officer limit USD 3,000,000 per instrument ≥ USD 2,000,000: within mandate | 300000000 |
| Applicant / beneficiary | `ORG_DEMO_01` (NL importer) / `ORG_DEMO_02` (US supplier) | |
| Product | Import documentary letter of credit, machine parts | |

---

## 2. Case A: `LC-001`, missing invoice (stage case)

### Revision 1 (no invoice)

| Check | Expected |
|---|---|
| Agent `missing_items` | `["supplier_invoice"]` |
| Owner of missing item | Coverage (relationship manager) |
| Agent must not | invent an invoice amount or supplier reference; mark anything as cleared |
| Credit Risk | `clear` · headroom after USD 500,000, within limit, expiry OK |
| Compliance | `hold` · reason code `DOCUMENT_REQUIRED` · request to `coverage` · required evidence `supplier_invoice` (Compliance needs the invoice to check the parties and goods for the trade corridor) |
| Trade Finance | **pending** (demo intake rule: Trade can't clear without the invoice) |
| Case status | `on_hold` |
| Final officer | sees "Waiting for Compliance"; Approve disabled; API returns 409 |
| Issuance receipts | 0 |

### Revision 2 (Coverage attaches `DOC-INV-01`)

| Check | Expected |
|---|---|
| Invoice content | must match the LC exactly: USD 2,000,000.00 · supplier `ORG_DEMO_02` · machine parts · pro forma, pre-issuance |
| Revision | 1 → **2** (material evidence added) |
| Prior clearances | all reset; Credit signs again on rev 2 |
| Compliance hold | stays open until Compliance clears with reason code `CHECKS_COMPLETE`, selects its open hold and cites `DOC-INV-01@1`. The upload alone does **not** clear it |
| Agent `missing_items` | `[]` |
| Findings | Trade `clear` · Credit `clear` (same numbers) · Compliance `clear` (resolves hold) |
| Status | `ready_for_decision` |
| Final officer | `approve` with reason |
| Operations | exactly **1** receipt `SIM-…` linked to rev 2; identical retry returns the same receipt |
| Final status | `issued_simulated` |

### Expected audit timeline (case A, in order)

| # | Event | Actor | Revision |
|---|---|---|---|
| 1 | Case created | Coverage | 1 |
| 2 | Agent run completed, packet sealed | Agent service | 1 |
| 3 | Credit Risk `clear` | Credit reviewer | 1 |
| 4 | Compliance `hold` `DOCUMENT_REQUIRED` + request to Coverage | Compliance reviewer | 1 |
| 5 | Approve attempt denied (only if tested) | Final officer | 1 |
| 6 | Evidence `DOC-INV-01` added, revision created | Coverage | 2 |
| 7 | Agent run completed, packet sealed | Agent service | 2 |
| 8 | Trade Finance `clear` | Trade reviewer | 2 |
| 9 | Credit Risk `clear` | Credit reviewer | 2 |
| 10 | Compliance `clear`, resolves hold from event 4 | Compliance reviewer | 2 |
| 11 | Decision `approve` | Final officer | 2 |
| 12 | Simulated issuance `SIM-…` | Operations | 2 |

Desks 8 to 10 can happen in any order. Every event records its actor, UTC time and revision. In live mode the run records a BRANE trace reference when the provider supplies one.

---

## 3. Case B: `LC-002`, complete file + independent Compliance hold

Purpose: prove a Compliance hold **alone** blocks approval (E3).

| Check | Expected |
|---|---|
| Facts | same customer, supplier, facility and amounts as case A; the supplier invoice is present from the start |
| **Hold** | a human decision by the Compliance reviewer after reading the restricted screening file, which only Compliance can see. No data trigger is needed |
| Agent `missing_items` | `[]` |
| Trade | `clear` |
| Credit | `clear` (headroom after USD 500,000) |
| Compliance | `hold` · reason code `MANUAL_REVIEW` · restricted detail only in Compliance view |
| Status | `on_hold` |
| Final officer approve | blocked (409), even with 2 of 3 desks cleared |
| Other desks and Coverage see | "Waiting for Compliance." Never the screening file or its content |
| After Compliance resolves | `ready_for_decision` → approve → 1 receipt |

**Data setup:** LC-001 and LC-002 each have an independent synthetic facility snapshot. Simulated issuance records a case receipt. Both scenarios can be run side by side.

---

## 4. Console wording

Rows marked *(in console)* match the current code. The others are proposed wording for screens not yet worded.

| Screen / moment | Text shown |
|---|---|
| Coverage, request inbox (case A) *(in console)* | "Please supply the supplier invoice for this instrument." |
| Coverage, after upload *(in console)* | "Supplier invoice attached. All three desks must review the new revision." |
| Credit Risk, packet summary | "The facility has USD 2,500,000 available. Issuing this USD 2,000,000 letter of credit leaves USD 500,000. Currency and expiry match the facility." |
| Trade Finance policy passage *(in console)* | "The bank requires the supplier invoice before clearing Trade Finance." |
| Compliance, hold (case A) | Reason code `DOCUMENT_REQUIRED` · shared text: "Supplier invoice required." |
| Compliance, hold (case B) | Reason code `MANUAL_REVIEW`; no further detail outside Compliance |
| Final officer, blocked *(in console)* | "Waiting for Compliance." |
| Final officer, ready *(in console)* | "The mandated officer can record a decision." |
| Over mandate *(in console)* | "Refer this case to a higher credit authority." |
| Stale screen | "This file has changed since you opened it. Reload to review the current version." |
| BRANE unavailable | "Analysis unavailable. Review the last recorded handoff and retry." |
| Operations button | **Simulate issuance** · receipt label "Simulated receipt, no real instrument created" |

---

## 5. Extra control fixtures (optional designs)

These proposed examples specify desired outcomes. The built-in boundary tests use named fixtures with their own amounts.

| ID | Change vs case A | Expected |
|---|---|---|
| `LC-003` insufficient headroom | Request USD 2,600,000 (260000000) | Headroom after = −USD 100,000 → `insufficient` → Credit `hold`; approve blocked |
| `LC-004` over mandate | Facility `FAC-USD-02`: limit USD 10,000,000, drawn 2,000,000, committed 0 → headroom USD 8,000,000. Request USD 4,000,000 | Credit `within_limit` (after USD 4,000,000) but amount > mandate USD 3,000,000 → officer must `refer`; approve returns 409 |
| `LC-005` expiry mismatch | LC expiry 2027-06-30 > facility expiry 2027-03-31 | Capacity cannot be confirmed: Credit packet says "Credit capacity requires a verified facility snapshot." Credit holds (`FACILITY_EXCEPTION`); approve blocked. Agent reports it, doesn't change dates |
| `LC-006` isolation (E1) | Customer `ORG_DEMO_03`, different reviewers | Case A reviewers get uniform 404 on `LC-006` |

---

## 6. Machine-readable summary

```json
{
  "LC-001": {
    "rev1": {"headroom_before_minor": 250000000, "headroom_after_minor": 50000000, "credit_result": "within_limit",
             "missing_items": ["supplier_invoice"], "missing_owner": "coverage",
             "findings": {"trade_finance": "pending", "credit_risk": "clear", "compliance": "hold"},
             "hold_reason_code": "DOCUMENT_REQUIRED", "status": "on_hold", "approve_allowed": false, "receipts": 0},
    "rev2": {"evidence_added": "DOC-INV-01", "missing_items": [],
             "findings": {"trade_finance": "clear", "credit_risk": "clear", "compliance": "clear"},
             "status_before_decision": "ready_for_decision", "decision": "approve", "receipts": 1}
  },
  "LC-002": {
    "rev1": {"headroom_after_minor": 50000000, "missing_items": [],
             "findings": {"trade_finance": "clear", "credit_risk": "clear", "compliance": "hold"},
             "hold_reason_code": "MANUAL_REVIEW", "status": "on_hold", "approve_allowed": false, "receipts": 0}
  },
  "LC-003": {"headroom_after_minor": -10000000, "credit_result": "insufficient", "approve_allowed": false},
  "LC-004": {"headroom_after_minor": 400000000, "credit_result": "within_limit", "over_mandate": true, "expected_decision": "refer"},
  "LC-005": {"headroom_after_minor": null, "credit_result": "unknown", "approve_allowed": false},
  "LC-006": {"access_by_lc001_reviewers": 404}
}
```

## 7. Expected data routing (what the model may see)

Amounts, headroom, mandate and expiry checks are **computed by bank code**, never by the model. Numbers are inserted into the desk text by code. The cloud model only receives codes and placeholders.

| Data | Expected route | Rule |
|---|---|---|
| Public product or policy question | Direct cloud | CB-01 |
| Desk drafting request, e.g. `{"task":"draft_desk_packet","desk":"trade_finance","missing":["supplier_invoice"]}` | Cloud, with case identifiers as placeholders | CB-02 |
| Company names, signatory, facility ID | Placeholder before cloud; real names only in the bank lookup | CB-02, CB-05 |
| Amounts, limits, headroom, goods, pricing, supplier | Stay in bank code; not sent to the model | CB-02, CB-09 |
| Compliance restricted screening file | Local only or refused; other desks see only "Waiting for Compliance." | CB-03 |
| Invoice raw document `DOC-INV-01` | Not sent to the model; code reads amount, currency, supplier ref | CB-02 |
| BRANE unreachable | No model call; status "Analysis unavailable"; no new packet | CB-07 |

## Sources and template

Use the [submission policy matrix](../docs/evidence/submission-policy-matrix.csv) for cited requirements and the [official template](../docs/MAIN_Participant_Starter_Kit/MAIN_Policy_Matrix_Template.csv) for column definitions. Mark the provenance of synthetic bank policy separately from legal sources. Review the wording against the [build specification](../docs/corporate-banking-hackathon-spec.md) before submission.
