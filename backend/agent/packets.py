"""Facility arithmetic and validation for the bank's desk-packet contract."""

from dataclasses import dataclass
from datetime import date, datetime, timezone


@dataclass(frozen=True)
class Capacity:
    status: str
    source_ref: str | None
    before_minor: int | None = None
    after_minor: int | None = None
    blocker: str | None = None


def facility_source(snapshot):
    facility = snapshot.get("facility")
    version = facility.get("revision", 1) if isinstance(facility, dict) else 1
    ref = snapshot.get("facility_ref")
    return f"{ref}@{version}" if ref and type(version) is int and version > 0 else None


def calculate_capacity(snapshot):
    facility = snapshot.get("facility")
    source = facility_source(snapshot)
    if not isinstance(facility, dict) or not source:
        return Capacity("unknown", source, blocker="missing_facility")
    if snapshot.get("currency") != "USD" or facility.get("currency") != snapshot["currency"]:
        return Capacity("unknown", source, blocker="currency_mismatch")

    limit, drawn, committed = (facility.get(key) for key in ("limit_minor", "drawn_minor", "committed_minor"))
    amount = snapshot.get("amount_minor")
    if (type(amount) is not int or amount <= 0
            or any(type(value) is not int or value < 0 for value in (limit, drawn, committed))):
        return Capacity("unknown", source, blocker="invalid_amounts")
    try:
        clock = datetime.fromisoformat(snapshot["as_of"])
        if clock.utcoffset() is None:
            return Capacity("unknown", source, blocker="invalid_dates")
        today = clock.astimezone(timezone.utc).date()
        instrument_end = date.fromisoformat(snapshot["expiry"])
        facility_end = date.fromisoformat(facility["expiry"])
    except (ValueError, TypeError, KeyError):
        return Capacity("unknown", source, blocker="invalid_dates")
    if instrument_end < today or facility_end < today:
        return Capacity("unknown", source, blocker="expired")
    if facility_end < instrument_end:
        return Capacity("unknown", source, blocker="facility_expires_first")

    before = limit - drawn - committed
    after = before - amount
    return Capacity("insufficient" if after < 0 else "within_limit", source, before, after,
                    "insufficient_headroom" if after < 0 else None)


def headroom_after(snapshot):
    # Preserve the calculation used by the case service's decision gates.
    return calculate_capacity(snapshot).after_minor


def invoice_is_current(snapshot):
    ref = snapshot.get("invoice_ref")
    document = snapshot.get("invoice_document_id")
    return bool(document and ref == document + "@1" and ref in snapshot["evidence_refs"])


def request_for(desk, needs_invoice, capacity):
    if desk == "credit_risk":
        if capacity.status == "unknown":
            return ["facility_snapshot"], "request_facility"
        if capacity.status == "insufficient":
            return [], "refer_capacity"
        return [], "review"
    return (["supplier_invoice"], "request_invoice") if needs_invoice else ([], "review")


# Closed wording keeps unsupported numbers, private notes and false approvals out of the UI.
CREDIT_STATEMENTS = {
    "unknown": (
        "Credit capacity requires a verified facility snapshot.",
        "Verify the facility evidence before reviewing credit capacity.",
    ),
    "insufficient": (
        "The proposed instrument exceeds available headroom.",
        "Refer the credit shortfall for human review.",
    ),
    "within_limit": (
        "The facility covers the proposed instrument.",
        "Review the calculated facility capacity for the proposed instrument.",
    ),
}
TRADE_STATEMENTS = {
    True: ("Coverage must supply the supplier invoice.", "Trade Finance review awaits the supplier invoice."),
    False: ("The supplier invoice is on file for Trade Finance review.", "Review the invoice and current trade terms."),
}
COMPLIANCE_STATEMENTS = {
    True: ("Coverage must supply the supplier invoice.", "Request the supplier invoice from Coverage."),
    False: ("The supplier invoice is on file for Compliance review.", "Review the current intake evidence."),
}
BLOCKERS = {
    "missing_facility": "Facility snapshot is missing.",
    "currency_mismatch": "Facility and instrument currencies must match in USD.",
    "invalid_amounts": "Facility or instrument amounts are missing or invalid.",
    "invalid_dates": "Facility or instrument dates are missing or invalid.",
    "expired": "The facility or instrument is expired at the case date.",
    "facility_expires_first": "The facility expires before the instrument.",
    "insufficient_headroom": "The requested amount exceeds available facility headroom.",
}


def candidates(desk, *, case, capacity, sources, policies):
    invoice = case["invoice_ref"]
    ref_prefix = {"trade_finance": "TRADE-", "compliance": "INTAKE-"}.get(desk)
    facts = []
    limitations = []
    if desk == "credit_risk":
        ref = capacity.source_ref if capacity.source_ref in sources else case["intake_ref"]
        refs = [ref]
        if capacity.after_minor is not None:
            if ref != capacity.source_ref:
                raise ValueError("Facility evidence is unavailable")
            facts = [
                {"field": "headroom_before_minor", "value": capacity.before_minor, "source_ref": ref},
                {"field": "headroom_after_minor", "value": capacity.after_minor, "source_ref": ref},
            ]
        if capacity.blocker:
            limitations.append(BLOCKERS[capacity.blocker])
        wording = CREDIT_STATEMENTS[capacity.status]
    else:
        refs = [ref for ref in sources if ref.startswith(ref_prefix)]
        if len(refs) != 1:
            raise ValueError("Expected one desk evidence source")
        if desk == "trade_finance":
            facts = [{"field": "amount_minor", "value": case["amount_minor"], "source_ref": refs[0]}]
        if invoice:
            refs.append(invoice)
        wording = (TRADE_STATEMENTS if desk == "trade_finance" else COMPLIANCE_STATEMENTS)[not invoice]
    if not policies or any(ref not in sources for ref in refs):
        raise ValueError("Required evidence or policy source is unavailable")
    missing, action = request_for(desk, not invoice, capacity)
    return [
        {
            "desk": desk, "summary": summary, "facts": facts, "policy_refs": sorted(policies),
            "evidence_refs": sorted(refs), "missing_items": missing, "suggested_next_step": action,
            "limitations": limitations,
        }
        for summary in wording
    ]


def validate_draft(packet, permitted):
    """Accept only facts, wording and dispositions derived from the active task context."""
    if not isinstance(packet, dict) or set(packet) != set(permitted[0]):
        raise ValueError("Unexpected desk-packet schema")
    if not isinstance(packet["facts"], list) or any(
        not isinstance(fact, dict) or type(fact.get("value")) is not int for fact in packet["facts"]
    ):
        raise ValueError("Invalid monetary fact")
    if packet not in permitted:
        raise ValueError("Unsupported desk-packet content")
    return packet
