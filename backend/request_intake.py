"""Staff request forms and their mapping to bank-owned case snapshots."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from . import departments
from .store import ROLES, identifier, snapshot
from .workflow import Problem


class RequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    workflow_id: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=3, max_length=120)
    context: str = Field(min_length=2, max_length=160)
    requested_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    reference: str = Field(default="", max_length=80)
    amount_minor: int | None = Field(default=None, gt=0, le=99_999_999_999_999)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    notes: str = Field(default="", max_length=1200)


# The three entries are the field label and the two editable synthetic examples.
CONTEXT = {
    'LC': ('Goods or shipment', 'Precision milling equipment', 'Cold-chain spare parts'),
    'RM': ('Meeting topic', 'Expansion financing', 'Plant capacity review'),
    'UW': ('Facility purpose', 'Working capital', 'Seasonal inventory financing'),
    'SYN': ('Term to compare', 'Repayment schedule', 'Reporting frequency'),
    'LS': ('Covenant under review', 'Interest cover', 'Quarterly covenant test'),
    'PAY': ('Payment rail', 'SEPA Credit Transfer', 'SWIFT transfer'),
    'DOC': ('Document under review', 'Bill of lading', 'Shipment-date evidence'),
    'FX': ('Currency pair', 'EUR / USD', 'GBP / USD'),
    'COL': ('Collateral type', 'Cash variation margin', 'Government securities'),
    'CUS': ('Corporate action', 'Cash dividend distribution', 'Cash dividend record date'),
    'MA': ('Deal stage', 'Execution copy at signing', 'Counsel review of amended terms'),
    'RES': ('Publication type', 'Issuer forecast', 'Research release'),
    'CCR': ('Exposure category', 'Counterparty credit line', 'Collateralized counterparty exposure'),
    'MR': ('Limit category', 'Interest-rate curve sensitivity', 'Portfolio sensitivity limit'),
    'MOD': ('Model under review', 'Production calibration model', 'Challenger model'),
    'ORM': ('Business process', 'Settlement reconciliation', 'Payment release'),
    'TRE': ('Liquidity bucket', 'Wholesale funding outflows', 'Short-term funding variance'),
    'KYC': ('Document requested', 'Beneficial-owner proof of address', 'Renewal evidence checklist'),
    'AML': ('Review category', 'Restricted case handover', 'Evidence follow-up'),
    'LEG': ('Clause under review', 'Notice period', 'Amended notice provisions'),
    'SUR': ('Review category', 'Order sequence review', 'Order chronology verification'),
    'AUD': ('Control under review', 'Access recertification', 'Payment reconciliation'),
    'FIN': ('Reporting line', 'Prudential instrument return', 'Prudential reporting adjustment'),
    'ICT': ('Affected service', 'Regulatory reporting batch', 'Back-office processing service'),
    'HR': ('Case category', 'Payroll statement request', 'Payroll statement delivery'),
    'BUY': ('Procurement category', 'Technical support services', 'Support contract renewal'),
    'EXE': ('Decision forum', 'Board committee', 'Executive committee'),
}

# Amounts in minor units. Only workflows that use money offer these fields.
AMOUNTS = {
    'UW': ('Requested facility', 350_000_000),
    'SYN': ('Facility size', 750_000_000), 'LS': ('Loan balance', 62_500_000),
    'PAY': ('Payment amount', 1_875_000), 'DOC': ('Presentation amount', 4_250_000),
    'FX': ('Trade notional', 250_000_000), 'COL': ('Disputed amount', 7_500_000),
    'CCR': ('Reported exposure', 155_000_000), 'MR': ('Reported excess', 8_000_000),
    'TRE': ('Liquidity variance', 80_000_000), 'FIN': ('Reporting variance', 1_250_000),
    'BUY': ('Bid value', 9_500_000),
}


def members(p):
    return [*departments.reviewers(p), departments.approver(p)] if p else ROLES


def form(p, customer, group):
    code = p['code'] if p else 'LC'
    owner = departments.analyst(p) if p else 'coverage'
    context, first, second = CONTEXT[code]
    base = None if p else snapshot('intake', customer)
    amount = AMOUNTS.get(code) if p else ('Credit amount', base['amount_minor'])
    registered = code + '-DEMO-01' if p else base['invoice_document_id']
    titles = p['examples'] if p else ['Finance an equipment shipment', 'Issue credit for a parts shipment']
    examples = []
    for i, value in enumerate((first, second)):
        examples.append({'subject': titles[i], 'context': value, 'reference': registered if i == 0 else '',
                         'requested_date': ('2026-12-10', '2026-12-17')[i] if p else (base['expiry'], '2027-02-15')[i],
                         'amount_minor': amount[1] * (i + 1) if amount else None,
                         'currency': ('EUR' if p else base['currency']) if amount else None, 'notes': ''})
    return {'id': p['id'] if p else departments.TRADE, 'code': code, 'group': p['group'] if p else 'Trade finance',
            'title': p['workflow'] if p else 'Import letter of credit', 'desk': p['desk'] if p else 'Coverage',
            'owner_role': owner, 'desk_id': group[owner], 'decision_desk': p['desk'] + ' approver' if p else 'Mandated officer',
            'context_label': context, 'source_label': p['source'] if p else 'Supplier invoice',
            'date_label': 'Review by' if p else 'Credit expiry', 'min_date': '2026-11-20',
            'amount_label': amount[0] if amount else None, 'currencies': (['EUR', 'USD', 'GBP'] if p else ['USD']) if amount else [],
            'examples': examples}


def build(body, p, schema, customer):
    try:
        requested = date.fromisoformat(body.requested_date)
    except ValueError:
        raise Problem(422, 'invalid_date', 'Enter a valid calendar date.') from None
    if requested.isoformat() < schema['min_date']:
        raise Problem(422, 'invalid_date', 'Choose a date on or after the case date, ' + schema['min_date'] + '.')
    if schema['amount_label'] and (body.amount_minor is None or body.currency not in schema['currencies']):
        raise Problem(422, 'invalid_amount', 'Enter a positive amount in one of the listed currencies.')
    if not schema['amount_label'] and (body.amount_minor is not None or body.currency is not None):
        raise Problem(422, 'unexpected_amount', 'This workflow does not take a monetary amount.')
    registered = body.reference == schema['examples'][0]['reference']
    cid = identifier(schema['code'])
    if p:
        s = departments.new_snapshot(p, cid, customer, 1 if registered else 2)
        s['case_title'] = p['workflow']
    else:
        bank_invoice = schema['examples'][0]
        matches_terms = (body.amount_minor, body.currency) == (bank_invoice['amount_minor'], bank_invoice['currency'])
        s = snapshot(cid, customer, registered and matches_terms)
        if not matches_terms:
            # An amendment can attach a new, case-bound synthetic invoice for the entered terms.
            s['invoice_document_id'] = 'DOC-INV-' + cid
        s.update(amount_minor=body.amount_minor, currency=body.currency, expiry=body.requested_date)
    s['request_input'] = body.model_dump(exclude={'workflow_id'})
    return s
