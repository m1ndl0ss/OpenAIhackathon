# Redwood department workflows

Open a department from the desk picker. Each row has a named analyst and a different final approver. Where a partner appears in the last column, that desk also signs the current file. Use **Switch desk** to move between them. [Walk through a payment exception](../README.md#try-a-specialist-desk)

Each department has two synthetic cases. The first starts with a verified source. In the second, the analyst must check and attach the registered supporting record. That action creates a new revision with its own drafts and signatures. Either case can end with the listed internal outcome or a referral. A hold stays open until the desk that placed it releases it.

The organizer runs evidence review, policy review and a handover draft for each file. The evidence and policy links open the underlying bank-side records. Partner desks can read the brief, control and verification status. Detailed source text is available to the specialist and final approver. Only predefined drafting words may go through BRANE. M&A, AML & Financial Crime and Regulatory Surveillance use the internal route for every task. [Versioned definitions](../data/workflows/departments-v1.json) · [Drafting runtime](../backend/agent/runtime.py)

## Corporate banking

| Desk and workflow | Verified file | File awaiting verification | Final human action | Additional reviewer |
| --- | --- | --- | --- | --- |
| **Relationship Management**<br>[Meeting follow-up](../research/bank-data-classification/relationship-management.md) | `RM-001` Checklist after an expansion meeting | `RM-002` Follow-up call after a plant visit | Record follow-up for staff delivery | Coverage |
| **Lending & Underwriting**<br>[Credit-pack completeness](../research/bank-data-classification/lending-underwriting.md) | `UW-001` Working-capital pack missing a forecast | `UW-002` Seasonal facility pack awaiting a bank reference | Record underwriting evidence request | Credit Risk |
| **Syndicated Finance**<br>[Term-sheet comparison](../research/bank-data-classification/specialized-finance-syndication.md) | `SYN-001` Two lenders disagree on the repayment schedule | `SYN-002` Borrower draft changes reporting frequency | Record term-sheet differences | Trade Finance |
| **Loan Servicing**<br>[Covenant exception review](../research/bank-data-classification/loan-servicing-restructuring.md) | `LS-001` Interest cover below the review threshold | `LS-002` Quarterly covenant certificate awaiting verification | Record covenant exception referral | Credit Risk |
| **Payments & Cash**<br>[Payment exception triage](../research/bank-data-classification/payments-cash-correspondent.md) | `PAY-001` A payment returned after the account closed | `PAY-002` Return message awaiting a match to the original transfer | Confirm the return match | Operations |
| **Trade & Working Capital**<br>[Documentary discrepancy review](../research/bank-data-classification/trade-working-capital-finance.md) | `DOC-001` Bill of lading shows a late shipment | `DOC-002` A second presentation awaits shipment-date verification | Record documentary discrepancy | Trade Finance |

## Markets and securities

| Desk and workflow | Verified file | File awaiting verification | Final human action | Additional reviewer |
| --- | --- | --- | --- | --- |
| **FX & Derivatives**<br>[Pre-trade handover](../research/bank-data-classification/fx-rates-derivatives.md) | `FX-001` Forward value date awaiting confirmation | `FX-002` Hedge handover awaiting its approval record | Record pre-trade handover | Credit Risk |
| **Settlement & Collateral**<br>[Margin dispute triage](../research/bank-data-classification/settlement-collateral.md) | `COL-001` Collateral in transit on a partial margin dispute | `COL-002` Counterparty valuation awaiting reconciliation | Record margin-dispute handover | Operations |
| **Custody & Agency**<br>[Corporate-action notice review](../research/bank-data-classification/custody-trust-agency.md) | `CUS-001` Mandatory cash dividend notice | `CUS-002` Dividend notice with an unverified record date | Record corporate-action checklist | Operations |
| **Capital Markets & M&A · bank only**<br>[Deal-document review](../research/bank-data-classification/capital-markets-ma.md) | `MA-001` Signature page missing from an execution copy | `MA-002` Revised deal document awaiting counsel comparison | Record internal counsel handover | — |
| **Markets Research**<br>[Publication review](../research/bank-data-classification/markets-research.md) | `RES-001` Forecast needs a label before publication | `RES-002` Release draft missing a disclosure check | Record editorial review | — |

## Risk and control

| Desk and workflow | Verified file | File awaiting verification | Final human action | Additional reviewer |
| --- | --- | --- | --- | --- |
| **Counterparty Risk**<br>[Exposure review](../research/bank-data-classification/credit-counterparty-risk.md) | `CCR-001` Exposure approaching an internal limit | `CCR-002` Monitoring pack awaiting collateral confirmation | Record counterparty review | Credit Risk |
| **Market Risk**<br>[Limit-breach explanation](../research/bank-data-classification/market-risk.md) | `MR-001` Curve move pushes sensitivity above limit | `MR-002` Second limit event awaiting a driver check | Record limit-breach explanation | Credit Risk |
| **Model Risk**<br>[Validation finding summary](../research/bank-data-classification/model-risk.md) | `MOD-001` Calibration gap in a validation report | `MOD-002` Challenger results awaiting a documentation check | Record validation finding | — |
| **Operational Risk**<br>[Incident classification](../research/bank-data-classification/operational-risk.md) | `ORM-001` Reconciliation delay recorded as a near miss | `ORM-002` A control repair awaiting incident classification | Record incident classification | Operations |
| **Treasury**<br>[Liquidity variance review](../research/bank-data-classification/bank-treasury.md) | `TRE-001` Wholesale outflow above the funding plan | `TRE-002` Funding variance awaiting a driver sign-off | Record liquidity variance note | Mandated officer |
| **KYC & Onboarding**<br>[Missing-document follow-up](../research/bank-data-classification/kyc.md) | `KYC-001` Beneficial-owner address evidence outstanding | `KYC-002` A renewal file awaiting checklist verification | Record evidence request for delivery | Compliance |
| **AML & Financial Crime · bank only**<br>[Restricted investigation handover](../research/bank-data-classification/aml-sanctions-fraud.md) | `AML-001` Monitoring alert awaiting investigator handover | `AML-002` Screening review awaiting a source check | Accept restricted investigation handover | — |
| **Legal**<br>[Contract review](../research/bank-data-classification/legal.md) | `LEG-001` Notice periods differ between two clauses | `LEG-002` Contract amendment awaiting clause verification | Record clause review | — |
| **Regulatory Surveillance · bank only**<br>[Restricted surveillance review](../research/bank-data-classification/regulatory-compliance.md) | `SUR-001` Order sequence awaiting surveillance review | `SUR-002` Restricted order chronology awaiting verification | Record internal surveillance handover | — |
| **Internal Audit**<br>[Evidence-to-finding review](../research/bank-data-classification/internal-audit.md) | `AUD-001` Access review missing its attestation | `AUD-002` Follow-up sample awaiting an evidence check | Record audit finding for review | — |

## Group functions

| Desk and workflow | Verified file | File awaiting verification | Final human action | Additional reviewer |
| --- | --- | --- | --- | --- |
| **Finance & Reporting**<br>[Reporting exception review](../research/bank-data-classification/finance-tax-regulatory-reporting.md) | `FIN-001` Unmatched instrument in a prudential return | `FIN-002` Reporting adjustment waiting for reference validation | Record reporting exception handover | Operations |
| **IT & Data Governance**<br>[Service incident handover](../research/bank-data-classification/it-cyber-data-governance.md) | `ICT-001` Scheduled reporting job delayed | `ICT-002` Contained processing delay awaiting owner verification | Record service handover | — |
| **People & HR**<br>[Employee case routing](../research/bank-data-classification/hr.md) | `HR-001` Payroll statement requested | `HR-002` Statement enquiry awaiting secure-channel verification | Record HR routing decision | — |
| **Procurement**<br>[Bid clarification review](../research/bank-data-classification/procurement.md) | `BUY-001` Support hours missing from a supplier bid | `BUY-002` Renewal bid awaiting coverage verification | Record bid clarification | — |
| **Executive Office**<br>[Board action tracking](../research/bank-data-classification/executive-office.md) | `EXE-001` Routine status update awaiting a board action owner | `EXE-002` Committee action waiting for a due-date check | Record board action reminder | — |

## Verification

The staff API tests exercise both scenarios in all 26 departments. They cover an unassigned desk, a missing source, a hold spanning a revision, partner document visibility, distinct signatures, a final referral and a durable outcome after restarting. An additional check exercises each department’s permitted message set with a controlled transport. [Department regression tests](../tests/test_department_workflows.py)

The live rehearsal processed the first example in every department. The 23 BRANE-enabled workflows made 69 model calls. BRANE reported 57 cloud routes and 12 local-model routes. The other three departments prepared nine tasks inside the application with zero model calls. All 26 files reached a signed internal outcome. The report records each task, the observed route, the packet checks and the outcome reference. [Measured rehearsal](evidence/department-rehearsal-live.json) · [Reproduce the run](../tools/department_rehearsal.py)
