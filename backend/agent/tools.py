"""Read-only projection of the current case and its versioned policy library."""

from datetime import date

from .packets import Capacity, calculate_capacity, invoice_is_current

DESK_TOPICS = {
    "trade_finance": "supplier_invoice",
    "credit_risk": "facility_capacity",
    "compliance": "desk_review",
}
POLICY_TEXT = {
    "trade_finance": "The synthetic bank requires the supplier invoice before clearing Trade Finance.",
    "credit_risk": "The facility must cover the amount, currency and instrument expiry.",
    "compliance": "Request missing intake evidence from Coverage. Only the owning desk can resolve its hold.",
}
# These are versioned demo policy passages, not conclusions about legal requirements.
POLICY_EFFECTIVE = date(2026, 11, 1)
POLICY_REFS = {
    "trade_finance": "POL-TRADE-01@1",
    "credit_risk": "POL-CREDIT-01@1",
    "compliance": "POL-COMPLIANCE-01@1",
}


class CaseTools:
    def __init__(self, snapshot, catalog, read):
        self.snapshot = snapshot
        self.catalog = catalog
        self.read = read
        self.as_of = date.fromisoformat(snapshot["as_of"][:10])

    def case_facts(self):
        self.read()
        snapshot = self.snapshot
        intake = [ref for ref in snapshot["evidence_refs"] if ref.startswith("INTAKE-")]
        if len(intake) != 1 or intake[0] not in self.catalog:
            raise ValueError("Intake evidence is unavailable")
        return {
            "instrument": snapshot["instrument"], "amount_minor": snapshot["amount_minor"],
            "currency": snapshot["currency"], "expiry": snapshot["expiry"], "intake_ref": intake[0],
            "invoice_ref": snapshot["invoice_ref"] if invoice_is_current(snapshot) else None,
        }

    def facility_snapshot(self, desk):
        self.read()
        if desk != "credit_risk":
            raise PermissionError("Facility access is unavailable for this desk")
        result = calculate_capacity(self.snapshot)
        source = self.catalog.get(result.source_ref)
        if source is None:
            return Capacity("unknown", None, blocker="missing_facility")
        if desk not in source[1]:
            raise PermissionError("Facility evidence is unavailable")
        return result

    def evidence_index(self, desk):
        self.read()
        if desk not in DESK_TOPICS:
            raise PermissionError("Evidence access is unavailable for this desk")
        prefixes = {
            "trade_finance": ("TRADE-", "DOC-INV-"),
            "credit_risk": ("FAC-", "INTAKE-"),
            "compliance": ("INTAKE-", "DOC-INV-"),
        }[desk]
        return {
            ref: source["label"]
            for ref, (source, audience) in self.catalog.items()
            if desk in audience and ref.startswith(prefixes)
        }

    def policy_search(self, desk, topic, jurisdiction, as_of):
        self.read()
        if (desk not in DESK_TOPICS or DESK_TOPICS[desk] != topic
                or jurisdiction != "NL" or not POLICY_EFFECTIVE <= as_of <= self.as_of):
            raise PermissionError("Policy search is outside the assigned task")
        ref = POLICY_REFS[desk]
        if (ref not in self.snapshot["policy_refs"].get(desk, ())
                or ref not in self.catalog or desk not in self.catalog[ref][1]):
            raise PermissionError("Policy passage is unavailable for this desk")
        return {
            ref: {"text": POLICY_TEXT[desk], "effective_from": POLICY_EFFECTIVE.isoformat(),
                  "citation": "Clearance synthetic bank policy, " + ref}
        }
