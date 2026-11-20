"""Deliver revision-bound packets to the people assigned to review and decide a case."""

import json

from . import departments
from .store import DESKS, event, now
from .workflow import conflict, detail, require_open, valid_invoice

SERVICE = {"id": "case-service", "role": "workflow"}


def roles(profile):
    if profile:
        return departments.analyst(profile), departments.reviewers(profile), departments.approver(profile)
    return "coverage", DESKS, "final_officer"


def contacts(profile, assignments, names):
    owner, reviewers, final = roles(profile)

    def person(role):
        recipient = assignments[role]
        return {"id": recipient, "role": role, "name": names.get(recipient, recipient)}

    return {"owner": person(owner), "reviewers": [person(role) for role in reviewers], "final": person(final)}


def deliver(db, row, s, stage, sender):
    _, reviewers, final = roles(departments.profile(s))
    assignments = json.loads(row["assignments"])
    stamp = now()
    targets = reviewers if stage == "review" else (final,)
    inserted = db.executemany(
        "INSERT INTO approval_deliveries(case_id,revision,packet_hash,stage,desk,recipient_id,sent_at) "
        "VALUES(?,?,?,?,?,?,?) ON CONFLICT(case_id,revision,stage,desk) DO NOTHING",
        [(s["case_id"], s["revision"], row["packet_hash"], stage, role, assignments[role], stamp) for role in targets],
    ).rowcount
    if inserted:
        event(db, s, sender, "approval." + stage + "_sent", ", ".join(assignments[r] for r in targets))
    return bool(inserted)


def submit(db, row, s, actor):
    require_open(db, s)
    created = deliver(db, row, s, "review", actor)
    return (201 if created else 200), {"case_id": s["case_id"], "revision": s["revision"], "stage": "review"}


def require_delivery(db, row, s, actor, stage):
    task = db.execute(
        "SELECT 1 FROM approval_deliveries WHERE case_id=? AND revision=? AND packet_hash=? "
        "AND stage=? AND desk=? AND recipient_id=?",
        (s["case_id"], s["revision"], row["packet_hash"], stage, actor["role"], actor["id"]),
    ).fetchone()
    if not task:
        conflict("approval_not_sent", "This revision has not been sent to your approval inbox.")


def route_final_if_ready(db, row, s, actor, mode):
    if detail(db, row, s, actor, mode)["status"] == "ready_for_decision":
        deliver(db, row, s, "decision", SERVICE)


def restore_existing(db):
    # Seed/legacy API runs already offered their sealed packets directly to assigned reviewers.
    # Preserve in-progress signatures from earlier console versions. Unsent custom packets stay drafts.
    rows = db.execute(
        "SELECT c.assignments,r.* FROM cases c JOIN revisions r ON r.case_id=c.id AND r.revision=c.revision "
        "WHERE r.packet_hash IS NOT NULL AND NOT EXISTS (SELECT 1 FROM decisions WHERE case_id=c.id) "
        "AND NOT EXISTS (SELECT 1 FROM approval_deliveries WHERE case_id=c.id AND revision=r.revision)"
    ).fetchall()
    for row in rows:
        s = json.loads(row["snapshot"])
        if "request_input" in s and not db.execute("SELECT 1 FROM reviews WHERE case_id=? AND revision=?",
                                                   (s["case_id"], s["revision"])).fetchone():
            continue
        deliver(db, row, s, "review", SERVICE)
        _, _, final = roles(departments.profile(s))
        actor = {"role": final, "id": json.loads(row["assignments"])[final]}
        route_final_if_ready(db, row, s, actor, row["mode"])


def inbox(db, actor, mode):
    rows = db.execute(
        "SELECT d.case_id,d.stage FROM approval_deliveries d JOIN cases c ON c.id=d.case_id AND c.revision=d.revision "
        "JOIN revisions r ON r.case_id=c.id AND r.revision=c.revision AND r.packet_hash=d.packet_hash "
        "WHERE c.customer=? AND d.recipient_id=? AND d.desk=? AND r.mode=? "
        "AND NOT EXISTS (SELECT 1 FROM decisions WHERE case_id=c.id) "
        "AND (d.stage='decision' OR COALESCE((SELECT disposition FROM reviews WHERE case_id=c.id AND revision=c.revision "
        "AND desk=d.desk ORDER BY rowid DESC LIMIT 1),'pending')!='clear')",
        (actor["customer_ref"], actor["id"], actor["role"], mode),
    )
    return {item["case_id"]: item["stage"] for item in rows}


def display_status(status, sent):
    return "ready_for_review" if status == "in_review" and not sent else status


def present(db, row, s, view, actor, names):
    p = departments.profile(s)
    owner, _, _ = roles(p)
    plan = contacts(p, json.loads(row["assignments"]), names)
    deliveries = {d["desk"]: d for d in db.execute(
        "SELECT desk,sent_at,recipient_id FROM approval_deliveries WHERE case_id=? AND revision=? AND packet_hash=?",
        (s["case_id"], s["revision"], row["packet_hash"]),
    )}
    findings = {review["desk"]: review["disposition"] for review in view["reviews"]}
    holds = {hold["desk"] for hold in view["holds"]}
    for person in plan["reviewers"]:
        role = person["role"]
        delivery = deliveries.get(role)
        person["sent_at"] = delivery["sent_at"] if delivery else None
        person["status"] = ("hold" if role in holds else "signed" if findings.get(role) == "clear" else
                            "awaiting" if delivery else "not_sent")
    final = plan["final"]
    ready = view["status"] == "ready_for_decision"
    decision = view["decision"]
    final_delivery = deliveries.get(final["role"])
    final["sent_at"] = final_delivery["sent_at"] if final_delivery else None
    final["status"] = decision["decision"] if decision else "awaiting" if ready and final_delivery else "waiting"
    sent = any(person["sent_at"] for person in plan["reviewers"])
    current = bool(row["packet_hash"]) and row["mode"] == view["configured_mode"]
    plan["evidence_action"] = None
    if current and not decision:
        if p and not s["evidence_verified"]:
            plan["evidence_action"] = "verify"
        elif not p and not valid_invoice(s):
            plan["evidence_action"] = "attach_invoice"
    plan["can_send"] = current and not decision and not sent and actor["role"] == owner
    if decision:
        plan["stage"] = "closed"
    elif not current:
        plan["stage"] = "preparing" if not row["packet_hash"] else "other_mode"
    elif final["status"] == "awaiting":
        plan["stage"] = "decision"
    else:
        plan["stage"] = "review" if sent else "ready"
    if not sent:
        view["permitted_actions"] = [a for a in view["permitted_actions"] if a not in {"sign", "hold", "review"}]
    if final["status"] != "awaiting":
        view["permitted_actions"] = [a for a in view["permitted_actions"] if a not in {"decide", "complete", "refer"}]
    if plan["stage"] == "ready":
        view["next_action"] = "Send the sealed packet for desk review to " + ", ".join(u["name"] for u in plan["reviewers"]) + "."
    elif plan["stage"] == "decision":
        view["next_action"] = final["name"] + " has the request for final approval."
    view["status"] = display_status(view["status"], sent)
    view["human_approval"] = plan
    return view
