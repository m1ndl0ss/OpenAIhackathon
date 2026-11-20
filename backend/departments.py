"""Versioned department definitions, synthetic case snapshots and closed drafting vocabulary."""

import hashlib
import json
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[1] / "data/workflows/departments-v1.json").read_text())
PROFILES = {(p["id"], p["version"]): p for p in CATALOG}
CURRENT = {p["id"]: p for p in CATALOG}
LANES = ("evidence", "policy", "handover")
TRADE = "import-letter-of-credit"


def analyst(p):
    return "dept_" + p["code"].lower()


def approver(p):
    return analyst(p) + "_head"


def reviewers(p):
    return [r for r in (analyst(p), p["partner"]) if r]


ROLE_LABELS = {role: p["desk"] + suffix for p in CATALOG
               for role, suffix in ((analyst(p), " analyst"), (approver(p), " approver"))}


def staff_directory():
    return [
        {"id": "staff-" + role, "role": role, "name": p[seat]}
        for p in CATALOG for seat, role in (("analyst", analyst(p)), ("approver", approver(p)))
    ]


def profile(s):
    workflow_id = s.get("workflow_id", TRADE)
    return None if workflow_id == TRADE else PROFILES[(workflow_id, s["definition_version"])]


def new_snapshot(p, case_id, customer, example):
    return {
        "case_id": case_id, "customer_ref": customer, "workflow_id": p["id"],
        "definition_version": p["version"], "revision": 1, "example": example,
        "case_title": p["examples"][example - 1], "evidence_verified": example == 1,
        "as_of": "2026-11-20T14:00:00Z", "brane_policy_version": "fixture-v1",
    }


def seeds(customer, group):
    suffix = "" if customer == "ORG_DEMO_01" else "-" + hashlib.sha256(customer.encode()).hexdigest()[:8]
    for p in CATALOG:
        roles = [*reviewers(p), approver(p)]
        if not all(role in group for role in roles):
            continue
        for example in (1, 2):
            case_id = f"{p['code']}-{example:03}{suffix}"
            yield new_snapshot(p, case_id, customer, example), {role: group[role] for role in roles}


def sources(s, p):
    base = s["case_id"]
    owners = {analyst(p), approver(p)}
    assigned = owners | set(reviewers(p))
    def item(ref, title, detail, audience):
        return ref, ({"ref": ref, "label": title, "detail": detail}, audience)
    items = [
        item(base + "-INTAKE@1", "Case brief", s["case_title"], assigned),
        item(base + "-RULE@1", "Department review rule", p["control"], assigned),
        item(base + "-STATUS@" + str(s["revision"]), "Evidence status",
             "Supporting record verified." if s["evidence_verified"] else "Supporting record awaits verification.", assigned),
    ]
    if s["evidence_verified"]:
        items.append(item(base + "-SOURCE@1", p["source"], p["observations"][s["example"] - 1], owners))
    return dict(items)


def wordings(p, lane, step):
    if step not in ("verify", "review") or lane not in LANES:
        raise ValueError("Unregistered drafting task")
    if lane == "policy":
        return (p["control"], "Review the department control. " + p["control"])
    if step == "verify":
        source = p["source"].lower()
        if lane == "evidence":
            return (f"Verify the {source} before signing.", f"Ask the analyst to verify the {source}.")
        return (f"Return the file to its analyst for the {source}.",
                f"Record the outstanding {source} in the internal handover.")
    if lane == "evidence":
        return (p["check"], "For the evidence review, " + p["check"][0].lower() + p["check"][1:])
    return ("Prepare the following human action: " + p["outcome"] + ".",
            "Submit this action for human review: " + p["outcome"] + ".")


def task_id(p, lane):
    return f"department/{p['id']}/v{p['version']}/{lane}"


TASKS = {task_id(p, lane): (p, lane) for p in CATALOG for lane in LANES}


def candidates(s, p, catalog, read):
    step = "review" if s["evidence_verified"] else "verify"
    base = s["case_id"]
    result = {}
    for lane in LANES:
        read()
        refs = [base + "-INTAKE@1", base + "-STATUS@" + str(s["revision"])]
        if lane == "evidence" and s["evidence_verified"]:
            refs.append(base + "-SOURCE@1")
        policy = base + "-RULE@1"
        if any(ref not in catalog for ref in [*refs, policy]):
            raise ValueError("Missing registered source")
        result[lane] = [
            {"desk": lane, "summary": line, "facts": [], "policy_refs": [policy], "evidence_refs": refs,
             "missing_items": [] if s["evidence_verified"] else [p["source"]],
             "suggested_next_step": step, "limitations": []} for line in wordings(p, lane, step)
        ]
    return result
