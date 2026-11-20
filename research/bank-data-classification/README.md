# Corporate banking data classification research

**Scope:** 26 agent workflows and 204 field inventory entries for a representative Dutch corporate bank under EU rules. Each workflow has a synthetic case, its outbound payload or a blocked outcome, and five expected tests. Research snapshot: 20 November 2026.

Start with the [classification method](classification-method.md) for label definitions, handling rules and source verification. Then open a workflow to find the exact fields it uses, why they matter and what can reach the model. Labels are proposed for the listed use case. The referenced law, industry specification and bank-local policy question are recorded separately.

## Corporate banking

- [Relationship management — meeting follow-up](relationship-management.md)
- [Lending and underwriting — credit-pack completeness](lending-underwriting.md)
- [Specialized finance and syndication — term-sheet comparison](specialized-finance-syndication.md)
- [Loan servicing and restructuring — covenant exception review](loan-servicing-restructuring.md)
- [Payments, cash management and correspondent banking — payment exception triage](payments-cash-correspondent.md)
- [Trade and working-capital finance — documentary discrepancy review](trade-working-capital-finance.md)

## Markets and securities

- [FX, rates and derivatives — pre-trade handover](fx-rates-derivatives.md)
- [Settlement and collateral — margin dispute triage](settlement-collateral.md)
- [Custody, trust and agency — corporate-action notice review](custody-trust-agency.md)
- [Capital markets and M&A — deal-document review](capital-markets-ma.md)
- [Markets research — draft publication review](markets-research.md)

## Risk and control

- [Credit and counterparty risk — exposure review](credit-counterparty-risk.md)
- [Market risk — limit-breach explanation](market-risk.md)
- [Model risk — validation finding summary](model-risk.md)
- [Operational risk — incident classification](operational-risk.md)
- [Bank treasury — liquidity variance explanation](bank-treasury.md)
- [KYC — missing-document follow-up](kyc.md)
- [AML, sanctions and fraud — investigation handover](aml-sanctions-fraud.md)
- [Legal — contract review](legal.md)
- [Regulatory compliance — surveillance case preparation](regulatory-compliance.md)
- [Internal audit — evidence-to-finding review](internal-audit.md)

## Group functions

- [Finance, tax and regulatory reporting — reporting exception explanation](finance-tax-regulatory-reporting.md)
- [IT, cybersecurity and data governance — incident handover](it-cyber-data-governance.md)
- [HR — employee case routing](hr.md)
- [Procurement — bid comparison](procurement.md)
- [Executive office — board action tracking](executive-office.md)

## Reading the examples

Each profile gives a proposed transfer policy, a synthetic input and expected test outcomes. Redwood’s implemented drafting path uses registered wording and keeps the case data inside the bank. For measured outcomes, the department record gives each desk’s observed routes and signed decision. The policy matrix connects the implemented controls to their sources. [Department run](../../docs/evidence/department-rehearsal-live.json) · [Policy matrix](../../submission/MAIN_Policy_Matrix_Template.csv)
