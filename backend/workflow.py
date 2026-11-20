"""Corporate trade workflow. Call mutating operations inside a SQLite write transaction."""

import json

from . import departments, integrations
from .agent.packets import facility_source, headroom_after as headroom, invoice_is_current, validate_draft
from .agent.runtime import contexts
from .agent.tools import POLICY_TEXT
from .store import DESKS, ROLES, canonical, digest, event, identifier, now


class Problem(Exception):
    def __init__(self, status, code, message, next_action=None):
        self.status, self.code, self.message, self.next_action = status, code, message, next_action


def conflict(code, message):
    raise Problem(409, code, message, "Reload the current file.")


def unavailable():
    raise Problem(404, "not_found", "This resource is unavailable.")


def require_role(actor, roles):
    if actor["role"] not in roles:
        raise Problem(403, "forbidden", "Your assignment does not permit this action.")


def record(db, case_id, actor):
    row = db.execute(
        "SELECT c.assignments,c.customer,r.* FROM cases c JOIN revisions r "
        "ON r.case_id=c.id AND r.revision=c.revision WHERE c.id=?",
        (case_id,),
    ).fetchone()
    if (
        not row
        or actor["customer_ref"] != row["customer"]
        or not integrations.is_assigned(actor, json.loads(row["assignments"]))
    ):
        unavailable()
    return row, json.loads(row["snapshot"])


def on_version(s, revision):
    if revision != s["revision"]:
        conflict("stale_revision", "The evidence has changed. Review the current revision.")


def on_packet(r, s, body):
    on_version(s, body.revision)
    if not r["packet_hash"] or r["packet_hash"] != body.packet_hash:
        conflict("stale_packet", "The reviewed packet does not match the current sealed file.")


def require_open(db, s):
    if db.execute("SELECT 1 FROM decisions WHERE case_id=?", (s["case_id"],)).fetchone():
        conflict("case_final", "A final disposition already exists for this case.")


def active_reviews(db, s):
    rows = db.execute(
        "SELECT * FROM reviews WHERE case_id=? AND revision=? ORDER BY rowid", (s["case_id"], s["revision"])
    )
    return {row["desk"]: dict(row) for row in rows}


def active_holds(db, s):
    return [
        dict(x)
        for x in db.execute(
            "SELECT hold_id,desk,revision,reason_code FROM holds WHERE case_id=? "
            "AND resolved_event IS NULL ORDER BY rowid",
            (s["case_id"],),
        )
    ]


def valid_invoice(s):
    return invoice_is_current(s)


def capacity(s):
    value = current_headroom(s)
    return value is not None and value >= 0


def current_headroom(s):
    return headroom(s) if facility_source(s) in s["evidence_refs"] else None


def within_mandate(s):
    return (
        s["currency"] == s["mandate_currency"]
        and s["amount_minor"] <= s["mandate_minor"]
        and s["as_of"][:10] <= s["mandate_expiry"]
    )


def source_catalog(s):
    p = departments.profile(s)
    if p:
        return departments.sources(s, p)
    docs = {}

    def add(ref, label, detail, roles):
        docs[ref] = ({"ref": ref, "label": label, "detail": detail}, set(roles))

    for ref in s["evidence_refs"]:
        if ref.startswith("TRADE-"):
            add(
                ref, "Trade terms", "Documentary import credit. Instrument expiry " + s["expiry"] + ".", ROLES
            )
        elif ref.startswith("INTAKE-"):
            add(
                ref,
                "Intake request",
                "Signed synthetic intake for the applicant and instrument on this case.",
                ROLES,
            )
        elif ref == s["invoice_ref"]:
            add(
                ref,
                "Supplier invoice",
                "Checked invoice for " + s["supplier_ref"] + " in " + s["currency"] + ".",
                ROLES,
            )
        elif ref == facility_source(s):
            f = s.get("facility")
            detail = "Facility snapshot unavailable."
            if isinstance(f, dict):
                detail = (
                    f"{f.get('currency')} minor units: limit {f.get('limit_minor')}, "
                    f"drawn {f.get('drawn_minor')}, committed {f.get('committed_minor')}. "
                    f"Expires {f.get('expiry')}."
                )
            add(
                ref,
                "Facility snapshot",
                detail,
                ("credit_risk", "final_officer"),
            )
    add(
        s["screen_ref"],
        "Restricted screening file",
        "Synthetic Compliance-only screening record.",
        ("compliance",),
    )
    for desk, refs in s["policy_refs"].items():
        for ref in refs:
            add(
                ref,
                "Synthetic " + desk.replace("_", " ") + " policy",
                POLICY_TEXT[desk],
                (desk, "final_officer"),
            )
    return docs


def sources_for(s, role):
    return [v for v, roles in source_catalog(s).values() if role in roles]


def visible_run_analysis(db, run_id, role):
    row = db.execute("SELECT details FROM run_analysis WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        return None
    report = json.loads(row["details"])
    allowed_tasks = {"draft_" + role}
    if role in ("coverage", "final_officer"):
        allowed_tasks.update(("draft_trade_finance", "draft_credit_risk") if role == "final_officer"
                             else ("draft_trade_finance",))
    report["observations"] = [item for item in report["observations"] if item["task"] in allowed_tasks]
    return report


def recommendation(row, run, mode, s, role, status, next_action, p=None):
    if (not row["packet_hash"] or row["mode"] != mode or not run or run["status"] != "sealed"
            or run["run_id"] != row["run_id"] or status not in {"in_review", "on_hold", "ready_for_decision"}):
        return None
    packets = json.loads(row["packets"])
    if status == "on_hold":
        tone, title, guidance = "attention", "Resolve the open hold", next_action
    elif status == "ready_for_decision":
        tone, title, guidance = "review", "Desk signatures complete", next_action
    elif p:
        evidence = packets["evidence"]
        if evidence["missing_items"]:
            tone, title, guidance = "attention", "Verify the supporting record", evidence["summary"]
        else:
            tone, title, guidance = "review", "Ready for desk sign-off", evidence["summary"]
    elif not within_mandate(s):
        tone, title = "attention", "Refer to a higher credit authority"
        guidance = "The requested credit exceeds the officer’s mandate. The mandated officer must handle the referral."
    elif role in {"credit_risk", "final_officer"} and not capacity(s):
        tone, title, guidance = "attention", "Review the facility exception", packets["credit_risk"]["summary"]
    elif not valid_invoice(s):
        tone, title = "attention", "Collect the supplier invoice"
        guidance = "Coverage should attach the invoice for the requested amount and currency before the desks sign."
    else:
        tone, title = "review", "Ready for desk sign-off"
        guidance = "The invoice is on file. Trade Finance, Credit Risk and Compliance must each review their packet."
    return {"tone": tone, "title": title, "guidance": guidance}


def detail(db, r, s, actor, configured_mode="fixture"):
    p = departments.profile(s)
    if p:
        from . import department_case
        return department_case.detail(db, r, s, actor, configured_mode, p)
    case_id, role = s["case_id"], actor["role"]
    reviews = active_reviews(db, s)
    holds = active_holds(db, s)
    decision = db.execute("SELECT * FROM decisions WHERE case_id=?", (case_id,)).fetchone()
    receipt = db.execute("SELECT * FROM receipts WHERE case_id=?", (case_id,)).fetchone()
    run = db.execute(
        "SELECT run_id,revision,mode,status FROM runs WHERE case_id=? AND revision=? "
        "ORDER BY rowid DESC LIMIT 1",
        (case_id, s["revision"]),
    ).fetchone()
    if receipt:
        status, next_action = "issued_simulated", "Read the simulated receipt."
    elif decision:
        states = {
            "approve": ("approved", "Operations can simulate issuance."),
            "decline": ("declined", "Read the final disposition."),
            "refer": ("referred", "Higher credit authority must review the referral."),
        }
        status, next_action = states[decision["decision"]]
    elif holds:
        status = "on_hold"
        next_action = "Waiting for " + ", ".join(h["desk"].replace("_", " ").title() for h in holds) + "."
    elif not r["packet_hash"]:
        status, next_action = "preparing", "Coverage or the final officer can prepare the review packet."
    elif (
        all(reviews.get(d, {}).get("disposition") == "clear" for d in DESKS)
        and valid_invoice(s)
        and capacity(s)
    ):
        status, next_action = "ready_for_decision", "The mandated officer can record a decision."
    else:
        status, next_action = "in_review", "Assigned departments must review the current file."
    requests = []
    for req in db.execute(
        "SELECT * FROM requests WHERE case_id=? AND (from_desk=? OR to_desk=?) ORDER BY rowid",
        (case_id, role, role),
    ):
        item = dict(req)
        item["blocking"] = bool(req["hold_id"]) and req["status"] != "resolved"
        requests.append(item)
    permitted = []
    if not decision:
        if role in ("coverage", "final_officer") and not r["packet_hash"]:
            permitted.append("run")
        if role in DESKS and r["packet_hash"]:
            permitted.append("review")
        permitted.append("request")
        if any(q["to_desk"] == role and q["status"] == "open" for q in requests):
            permitted.append("reply")
        if role == "coverage" and not s["invoice_ref"]:
            permitted.append("attach_invoice")
        if role == "final_officer" and status == "ready_for_decision":
            permitted.append("decide")
    if role == "operations" and status == "approved":
        permitted.append("issue")
    if r["packet_hash"] and r["mode"] != configured_mode:
        permitted = [action for action in permitted if action not in ("review", "decide", "issue")]
        next_action = "Open a new case to work in the configured analysis mode."
    findings = []
    for desk, review in reviews.items():
        fields = ["desk", "disposition", "event_id", "actor_id", "reason_code", "revision"]
        if desk == role:
            fields.append("reason")
        findings.append({key: review[key] for key in fields})
    drafts = json.loads(r["packets"]) if r["packets"] else {}
    packets = [
        drafts[d]
        for d in DESKS
        if d in drafts and (d == role or (role == "final_officer" and d != "compliance"))
    ]
    decision_view = dict(decision) if decision else None
    if decision_view and role != "final_officer":
        decision_view.pop("reason")
    intake = s.get("request_input") if role in {"coverage", "final_officer"} else None
    return {
        "case_id": case_id, "workflow_id": departments.TRADE, "definition_version": 1,
        "workflow_title": "Import letter of credit", "department": "Trade Finance",
        "case_title": intake["subject"] if intake else "Import letter of credit",
        "request_input": intake,
        "recommendation": recommendation(r, run, configured_mode, s, role, status, next_action),
        "customer_ref": s["customer_ref"],
        "revision": s["revision"],
        "status": status,
        "next_action": next_action,
        "amount_minor": s["amount_minor"],
        "currency": s["currency"],
        "facility_ref": s["facility_ref"],
        "instrument": s["instrument"],
        "expiry": s["expiry"],
        "as_of": s["as_of"],
        "invoice_ref": s["invoice_ref"],
        "invoice_document_id": s["invoice_document_id"],
        "packet_hash": r["packet_hash"],
        "mode": r["mode"],
        "configured_mode": configured_mode,
        "analysis_available": integrations.analysis_ready(configured_mode),
        "mandate_minor": s["mandate_minor"],
        "mandate_currency": s["mandate_currency"],
        "within_mandate": within_mandate(s),
        "headroom_after_minor": current_headroom(s) if role in ("credit_risk", "final_officer") else None,
        "permitted_actions": permitted,
        "reviews": findings,
        "holds": holds,
        "requests": requests,
        "packets": packets,
        "sources": sources_for(s, role),
        "decision": decision_view,
        "receipt": dict(receipt) if receipt else None,
        "last_run": {**dict(run), "analysis": visible_run_analysis(db, run["run_id"], role)} if run else None,
    }


def validate_packets(s, packets):
    expected = contexts(s, source_catalog(s), lambda: None)
    if not isinstance(packets, dict) or set(packets) != set(expected):
        raise ValueError("Incomplete desk bundle")
    for desk, packet in packets.items():
        validate_draft(packet, expected[desk])


def local_document(s):
    return {
        "id": s["invoice_document_id"],
        "version": 1,
        "case_id": s["case_id"],
        "customer_ref": s["customer_ref"],
        "supplier_ref": s["supplier_ref"],
        "amount_minor": s["amount_minor"],
        "currency": s["currency"],
    }


def seal(db, s, packets, run):
    validate_packets(s, packets)
    catalog = source_catalog(s)
    manifest = {
        "case": {**s, "brane_policy_version": run.get("policy_version", s["brane_policy_version"])},
        "documents": {ref: digest(doc) for ref, (doc, _) in sorted(catalog.items())},
        "desks": {desk: digest(packet) for desk, packet in packets.items()},
        "mode": run["mode"],
    }
    if valid_invoice(s):
        manifest["documents"][s["invoice_ref"]] = digest(local_document(s))
    packet_hash = digest(manifest)
    db.execute(
        "UPDATE revisions SET packets=?,packet_hash=?,mode=?,sealed_at=?,run_id=? WHERE case_id=? AND revision=?",
        (canonical(packets), packet_hash, run["mode"], now(), run["run_id"], s["case_id"], s["revision"]),
    )
    return packet_hash


INVOICE_QUESTION = "Please supply the supplier invoice for this instrument."
COMPLIANCE_QUESTIONS = {INVOICE_QUESTION, "Please confirm the current case evidence for Compliance review."}
COMPLIANCE_REPLY = "Compliance has reviewed the request. See the current desk disposition."


def create_request(db, s, actor, to_desk, question, hold_id=None):
    if actor["role"] == "compliance" and question not in COMPLIANCE_QUESTIONS:
        raise Problem(422, "restricted_text", "Choose an approved shareable Compliance question.")
    if actor["role"] == to_desk:
        raise Problem(422, "invalid_recipient", "Choose another assigned desk.")
    request_id = identifier("REQ")
    db.execute(
        "INSERT INTO requests(request_id,case_id,revision,from_desk,to_desk,question,status,hold_id)"
        " VALUES(?,?,?,?,?,?,'open',?)",
        (request_id, s["case_id"], s["revision"], actor["role"], to_desk, question, hold_id),
    )
    event(db, s, actor, "request.created", "Question sent to " + to_desk.replace("_", " ") + ".")
    return request_id


def review(db, r, s, actor, body):
    from .approvals import require_delivery

    on_packet(r, s, body)
    require_open(db, s)
    require_delivery(db, r, s, actor, "review")
    desk = actor["role"]
    prior = active_reviews(db, s).get(desk)
    if body.expected_review_event_id != (prior["event_id"] if prior else None):
        conflict("stale_review", "A newer finding exists for this desk.")
    holds = [h for h in active_holds(db, s) if h["desk"] == desk]
    owned = {h["hold_id"] for h in holds}
    if body.disposition == "clear":
        if body.reason_code != "CHECKS_COMPLETE" or body.request_to or body.required_evidence:
            raise Problem(422, "invalid_finding", "Choose the clearance reason without a new request.")
        if (desk == "trade_finance" and not valid_invoice(s)) or (desk == "credit_risk" and not capacity(s)):
            conflict("evidence_incomplete", "This desk's required evidence does not support clearance.")
        if set(body.resolves_hold_ids) != owned:
            conflict(
                "hold_resolution_required",
                "Select all open holds owned by this desk and cite reviewed evidence.",
            )
        allowed = {item["ref"] for item in sources_for(s, desk)}
        if owned and body.evidence_ref not in allowed:
            conflict("evidence_required", "An authorised current evidence reference is required.")
        if any(h["reason_code"] == "DOCUMENT_REQUIRED" for h in holds) and (
            not valid_invoice(s) or body.evidence_ref != s["invoice_ref"]
        ):
            conflict("invoice_required", "Review and cite the current supplier invoice.")
    else:
        if body.reason_code not in ("DOCUMENT_REQUIRED", "MANUAL_REVIEW", "FACILITY_EXCEPTION"):
            raise Problem(422, "invalid_reason_code", "Choose a supported hold reason.")
        if body.resolves_hold_ids or body.evidence_ref:
            raise Problem(422, "invalid_hold", "A hold cannot resolve a previous finding.")
        if holds:
            conflict("open_hold", "This desk already owns an unresolved hold.")
        if body.required_evidence or body.request_to:
            if (
                body.reason_code != "DOCUMENT_REQUIRED"
                or body.required_evidence != "supplier_invoice"
                or body.request_to != "coverage"
            ):
                raise Problem(422, "invalid_request", "Choose the supplier invoice request for Coverage.")
    review_id = event(db, s, actor, "review." + body.disposition, body.reason_code)
    db.execute(
        "INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            review_id,
            s["case_id"],
            s["revision"],
            desk,
            body.disposition,
            actor["id"],
            body.reason_code,
            body.reason,
            r["packet_hash"],
            body.expected_review_event_id,
        ),
    )
    if body.disposition == "hold":
        hold_id = identifier("HOLD")
        db.execute(
            "INSERT INTO holds(hold_id,case_id,revision,desk,reason_code) VALUES(?,?,?,?,?)",
            (hold_id, s["case_id"], s["revision"], desk, body.reason_code),
        )
        if body.request_to:
            create_request(
                db,
                s,
                actor,
                body.request_to,
                INVOICE_QUESTION,
                hold_id,
            )
    else:
        for hold_id in owned:
            db.execute("INSERT INTO hold_resolutions VALUES(?,?,?)", (hold_id, review_id, body.evidence_ref))
            db.execute("UPDATE holds SET resolved_event=? WHERE hold_id=?", (review_id, hold_id))
            db.execute("UPDATE requests SET status='resolved' WHERE hold_id=?", (hold_id,))
        if owned:
            event(db, s, actor, "hold.resolved", "Reviewed evidence and released the desk hold.")
    return {"event_id": review_id, "revision": s["revision"], "disposition": body.disposition}


def add_invoice(db, r, s, actor, body):
    require_open(db, s)
    on_version(s, body.expected_revision)
    if body.fixture_document_id != s["invoice_document_id"]:
        unavailable()
    if valid_invoice(s):
        conflict("invoice_attached", "The fixture invoice has already been attached.")
    if body.request_id:
        req = db.execute(
            "SELECT * FROM requests WHERE case_id=? AND request_id=? AND to_desk=?",
            (s["case_id"], body.request_id, actor["role"]),
        ).fetchone()
        if not req:
            unavailable()
        if req["status"] == "resolved":
            conflict("request_resolved", "This request has already been resolved.")
    s["revision"] += 1
    s["invoice_ref"] = s["invoice_document_id"] + "@1"
    s["evidence_refs"] = sorted(s["evidence_refs"] + [s["invoice_ref"]])
    db.execute("UPDATE cases SET revision=? WHERE id=?", (s["revision"], s["case_id"]))
    db.execute(
        "INSERT INTO revisions(case_id,revision,snapshot) VALUES(?,?,?)",
        (s["case_id"], s["revision"], canonical(s)),
    )
    if body.request_id:
        db.execute(
            "UPDATE requests SET status='answered',reply=?,evidence_ref=?,answered_revision=? WHERE request_id=?",
            (body.note, s["invoice_ref"], s["revision"], body.request_id),
        )
        event(db, s, actor, "request.answered", "Coverage supplied the requested evidence.")
    event(
        db,
        s,
        actor,
        "evidence.attached",
        "Supplier invoice attached. All three desks must review the new revision.",
    )
    return {"revision": s["revision"], "invoice_ref": s["invoice_ref"]}


def decide(db, r, s, actor, body):
    from .approvals import require_delivery

    on_packet(r, s, body)
    require_open(db, s)
    view = detail(db, r, s, actor)
    if view["status"] != "ready_for_decision":
        conflict("review_incomplete", "All three current desk clearances and no open holds are required.")
    require_delivery(db, r, s, actor, "decision")
    if not within_mandate(s) and body.decision != "refer":
        conflict("mandate_exceeded", "Refer this case to a higher credit authority.")
    timestamp = now()
    db.execute(
        "INSERT INTO decisions VALUES(?,?,?,?,?,?,?)",
        (s["case_id"], s["revision"], r["packet_hash"], actor["id"], body.decision, body.reason, timestamp),
    )
    event(
        db,
        s,
        actor,
        "decision." + body.decision,
        "Referred to higher credit authority."
        if body.decision == "refer"
        else "Final human disposition recorded.",
    )
    return {
        "decision": body.decision,
        "revision": s["revision"],
        "actor_id": actor["id"],
        "packet_hash": r["packet_hash"],
        "timestamp": timestamp,
    }


def issue(db, r, s, actor, body):
    on_packet(r, s, body)
    decision = db.execute("SELECT * FROM decisions WHERE case_id=?", (s["case_id"],)).fetchone()
    if not decision or decision["decision"] != "approve" or decision["packet_hash"] != r["packet_hash"]:
        conflict("approval_required", "Operations requires an approved current file.")
    receipt = db.execute("SELECT * FROM receipts WHERE case_id=?", (s["case_id"],)).fetchone()
    if receipt:
        return 200, dict(receipt)
    db.execute(
        "INSERT INTO receipts VALUES(?,?,?,?,?,?)",
        (s["case_id"], identifier("SIM"), s["revision"], r["packet_hash"], actor["id"], now()),
    )
    event(db, s, actor, "receipt.issued", "Operations recorded a simulated issuance.")
    receipt = db.execute("SELECT * FROM receipts WHERE case_id=?", (s["case_id"],)).fetchone()
    return 201, dict(receipt)
