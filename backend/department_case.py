"""Department case projections and human actions on the shared revision and audit store."""

import json

from . import departments as dep, integrations
from .store import canonical, event, identifier, now
from .workflow import Problem, active_holds, active_reviews, conflict, on_version, recommendation, require_open, revision_run


def state(db, row, s, p):
    reviews = active_reviews(db, s)
    holds = active_holds(db, s)
    decision = db.execute("SELECT * FROM decisions WHERE case_id=?", (s["case_id"],)).fetchone()
    if decision:
        status = "completed" if decision["decision"] == "approve" else "referred"
    elif holds:
        status = "on_hold"
    elif not row["packet_hash"]:
        status = "preparing"
    elif s["evidence_verified"] and all(reviews.get(role, {}).get("disposition") == "clear" for role in dep.reviewers(p)):
        status = "ready_for_decision"
    else:
        status = "in_review"
    return status, reviews, holds, decision


def role_labels(p):
    return {dep.analyst(p): p["desk"] + " analyst", dep.approver(p): p["desk"] + " approver"}


def actions(row, s, p, role, status, reviews, holds, mode):
    if status in ("completed", "referred"):
        return []
    result = []
    owner, head = dep.analyst(p), dep.approver(p)
    if role == owner and not s["evidence_verified"]:
        result.append("verify")
    if not row["packet_hash"]:
        if role in (owner, head):
            result.append("run")
        return result
    if row["mode"] != mode:
        return result
    if role in dep.reviewers(p):
        if s["evidence_verified"] and reviews.get(role, {}).get("disposition") != "clear":
            result.append("sign")
        if not any(h["desk"] == role for h in holds):
            result.append("hold")
    if role == head and status == "ready_for_decision":
        result.extend(("complete", "refer"))
    return result


def next_action(status, s, p, sealed):
    if status in ("completed", "referred"):
        return "Read the recorded department outcome."
    if not s["evidence_verified"]:
        return "The analyst must verify the supporting record: " + p["source"] + "."
    if not sealed:
        return "Run the organizer to prepare the three review packets."
    if status == "on_hold":
        return "The desk that placed the hold must review the evidence and release it."
    if status == "ready_for_decision":
        return "The department approver can record the final disposition."
    return "The assigned reviewers must sign the current evidence and draft."


def summary(db, row, s, p, role, status=None):
    status = status or state(db, row, s, p)[0]
    intake = s.get("request_input") if role in (dep.analyst(p), dep.approver(p)) else None
    return {k: s[k] for k in ("case_id", "customer_ref", "revision", "workflow_id", "definition_version")} | {
        "case_title": intake["subject"] if intake else s["case_title"],
        "amount_minor": intake["amount_minor"] if intake else None, "currency": intake["currency"] if intake else None,
        "workflow_title": p["workflow"], "department": p["desk"], "status": status,
        "next_action": next_action(status, s, p, row["packet_hash"]),
    }


def detail(db, row, s, actor, mode, p):
    role, cid = actor["role"], s["case_id"]
    status, reviews, holds, decision = state(db, row, s, p)
    source_list = [value for value, audience in dep.sources(s, p).values() if role in audience]
    permitted_refs = {ref["ref"] for ref in source_list}
    packets = json.loads(row["packets"]) if row["packets"] else {}
    projected = [{**packets[lane], "evidence_refs": [r for r in packets[lane]["evidence_refs"] if r in permitted_refs]}
                 for lane in dep.LANES if lane in packets]
    run = revision_run(db, row)
    final = dict(decision) if decision else None
    if final and role != dep.approver(p):
        final.pop("reason")
    receipt = db.execute("SELECT * FROM receipts WHERE case_id=?", (cid,)).fetchone()
    report = None
    if run:
        analysis = db.execute("SELECT details FROM run_analysis WHERE run_id=?", (run["run_id"],)).fetchone()
        report = json.loads(analysis["details"]) if analysis else None
    return {
        **summary(db, row, s, p, role, status),
        "request_input": s.get("request_input") if role in (dep.analyst(p), dep.approver(p)) else None,
        "recommendation": recommendation(row, run, mode, s, role, packets, source_list, p),
        "department_case": {"analyst": dep.analyst(p), "approver": dep.approver(p),
                            "reviewers": dep.reviewers(p), "role_labels": role_labels(p),
                            "local_only": p["local_only"], "source": p["source"], "outcome": p["outcome"], "examples": p["examples"],
                            "evidence_verified": s["evidence_verified"]},
        "mode": row["mode"], "configured_mode": mode,
        "analysis_available": p["local_only"] or integrations.analysis_ready(mode),
        "packet_hash": row["packet_hash"], "as_of": s["as_of"],
        "permitted_actions": actions(row, s, p, role, status, reviews, holds, mode),
        "reviews": [{k: v for k, v in entry.items() if k in ("desk", "disposition", "event_id", "actor_id", "reason_code", "revision")
                     or (k == "reason" and role == entry["desk"])} for entry in reviews.values()],
        "holds": holds, "requests": [], "sources": source_list, "packets": projected,
        "decision": final, "receipt": dict(receipt) if receipt else None,
        "last_run": {**dict(run), "analysis": report} if run else None,
    }


def apply(db, row, s, actor, body, mode):
    from .approvals import require_delivery

    p = dep.profile(s)
    role, cid, revision, action = actor["role"], s["case_id"], s["revision"], body.action
    require_open(db, s)
    on_version(s, body.revision)
    status, reviews, holds, _ = state(db, row, s, p)
    eligible = {"verify": [dep.analyst(p)], "sign": dep.reviewers(p), "hold": dep.reviewers(p),
                "complete": [dep.approver(p)], "refer": [dep.approver(p)]}
    if role not in eligible[action]:
        raise Problem(403, "forbidden", "This action requires its assigned human reviewer.")
    if action not in actions(row, s, p, role, status, reviews, holds, mode):
        conflict("action_unavailable", "Review the current evidence, holds and outstanding signatures.")
    if action == "verify":
        revised = {**s, "revision": revision + 1, "evidence_verified": True}
        db.execute("UPDATE cases SET revision=? WHERE id=?", (revision + 1, cid))
        db.execute("INSERT INTO revisions(case_id,revision,snapshot) VALUES(?,?,?)", (cid, revision + 1, canonical(revised)))
        event(db, revised, actor, "evidence.verified", "Supporting record verified. Review the new revision.")
        return 201, {"revision": revision + 1}
    if not row["packet_hash"] or body.packet_hash != row["packet_hash"]:
        conflict("stale_packet", "Review the current sealed packet.")
    require_delivery(db, row, s, actor, "review" if action in ("sign", "hold") else "decision")
    if not body.reason or len(body.reason.strip()) < 10:
        raise Problem(422, "reason_required", "Enter a reason of at least ten characters.")
    if action in ("sign", "hold"):
        old = reviews.get(role, {}).get("event_id")
        if old != body.expected_event_id:
            conflict("stale_review", "The desk finding has changed.")
        disposition = "clear" if action == "sign" else "hold"
        code = "CHECKS_COMPLETE" if action == "sign" else "MANUAL_REVIEW"
        eid = event(db, s, actor, "review." + disposition, code)
        db.execute("INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?,?,?)", (
            eid, cid, revision, role, disposition, actor["id"], code, body.reason, row["packet_hash"], old))
        if action == "hold":
            db.execute("INSERT INTO holds VALUES(?,?,?,?,?,NULL)", (identifier("HOLD"), cid, revision, role, code))
        else:
            for h in holds:
                if h["desk"] == role:
                    ref = cid + ("-SOURCE@1" if role == dep.analyst(p) else "-STATUS@" + str(revision))
                    db.execute("INSERT INTO hold_resolutions VALUES(?,?,?)", (h["hold_id"], eid, ref))
                    db.execute("UPDATE holds SET resolved_event=? WHERE hold_id=?", (eid, h["hold_id"]))
                    event(db, s, actor, "hold.resolved", "The owning reviewer released the hold.")
        return 201, {"event_id": eid, "disposition": disposition, "revision": revision}
    decision = "approve" if action == "complete" else "refer"
    stamp, receipt = now(), identifier("OUT")
    db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?)", (cid, revision, row["packet_hash"], actor["id"],
                                                               decision, body.reason, stamp))
    db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)", (cid, receipt, revision, row["packet_hash"], actor["id"], stamp))
    event(db, s, actor, "decision." + decision, p["outcome"] if decision == "approve" else "Referred for further review.")
    return 201, {"receipt_id": receipt, "decision": decision, "revision": revision}
