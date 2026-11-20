"""Deterministic, offline desk packets for exercising the human workflow."""

from datetime import date


def headroom_after(snapshot):
    facility = snapshot.get("facility") or {}
    currency = snapshot.get("currency")
    if not isinstance(facility, dict) or not currency or facility.get("currency") != currency:
        return None
    fields = [facility.get(key) for key in ("limit_minor", "drawn_minor", "committed_minor")]
    amount = snapshot.get("amount_minor")
    if (type(amount) is not int or amount <= 0
            or any(type(value) is not int or value < 0 for value in fields)):
        return None
    try:
        today = date.fromisoformat(snapshot["as_of"][:10])
        expiry = date.fromisoformat(snapshot["expiry"])
        if expiry < today or date.fromisoformat(facility["expiry"]) < expiry:
            return None
    except (ValueError, TypeError, KeyError):
        return None
    limit, drawn, committed = fields
    return limit - drawn - committed - amount


def fixture_packets(snapshot, report=None):
    invoice = snapshot.get("invoice_ref")
    facility_ref = f"{snapshot['facility_ref']}@1"
    refs = snapshot["evidence_refs"]

    def source_for(prefix):
        matches = [ref for ref in refs if ref.startswith(prefix)]
        if len(matches) != 1:
            raise RuntimeError("Case source missing or ambiguous.")
        return matches[0]

    remaining = headroom_after(snapshot)
    packets = {}
    for desk, source, policy in (
        ("trade_finance", source_for("TRADE-"), "POL-TRADE-01@1"),
        ("credit_risk", facility_ref, "POL-CREDIT-01@1"),
        ("compliance", source_for("INTAKE-"), "POL-COMPLIANCE-01@1"),
    ):
        if report:
            report(desk, "started")
        missing = desk != "credit_risk" and not invoice
        packet = {
            "desk": desk,
            "summary": "Review the current intake evidence." if not missing else "Coverage must supply the supplier invoice.",
            "facts": [],
            "policy_refs": [policy],
            "evidence_refs": [source],
            "missing_items": ["supplier_invoice"] if missing else [],
            "suggested_next_step": "request_invoice" if missing else "review",
            "limitations": [],
        }
        if invoice and desk != "credit_risk":
            packet["evidence_refs"].append(invoice)
        if desk == "trade_finance":
            packet["facts"].append({"field": "amount_minor", "value": snapshot["amount_minor"], "source_ref": source})
        if desk == "credit_risk":
            if remaining is None:
                packet["summary"] = "Credit capacity requires a verified facility snapshot."
                packet["limitations"].append("Facility inputs are incomplete or incompatible.")
            else:
                packet["facts"].append({"field": "headroom_after_minor", "value": remaining, "source_ref": source})
                packet["summary"] = ("The facility covers the proposed instrument." if remaining >= 0
                                     else "The proposed instrument exceeds available headroom.")
        packets[desk] = packet
        if report:
            report(desk, "prepared")
    return packets
