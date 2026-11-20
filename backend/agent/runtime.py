"""A bounded run for the letter-of-credit review agent."""

import json
from dataclasses import dataclass, field
from time import monotonic

from .packets import candidates, validate_draft
from .tools import DESK_TOPICS, CaseTools

MAX_MODEL_CALLS = 6
MAX_TOOL_READS = 8
RUN_SECONDS = 60
SYSTEM = (
    "Choose one approved wording for the assigned human desk and its next step. "
    "Return a JSON object with the single key summary containing the chosen wording verbatim."
)


@dataclass(frozen=True)
class ModelTurn:
    route: str
    completion: str | None = None
    observation: dict = field(default_factory=dict)
    transient: bool = False


@dataclass(frozen=True)
class AnalysisResult:
    case_ref: str
    revision: int
    run_id: str
    mode: str
    policy_version: str
    status: str
    packets: dict | None
    observations: list
    model_calls: int
    tool_reads: int
    reason: str | None = None


class BudgetExceeded(Exception):
    pass


class RunBudget:
    def __init__(self):
        self.deadline = monotonic() + RUN_SECONDS
        self.model_calls = 0
        self.tool_reads = 0
        self.retried = False

    def remaining(self):
        seconds = self.deadline - monotonic()
        if seconds <= 0:
            raise BudgetExceeded
        return seconds

    def read(self):
        self.remaining()
        if self.tool_reads >= MAX_TOOL_READS:
            raise BudgetExceeded
        self.tool_reads += 1

    def call(self):
        self.remaining()
        if self.model_calls >= MAX_MODEL_CALLS:
            raise BudgetExceeded
        self.model_calls += 1


def contexts(snapshot, catalog, read):
    tools = CaseTools(snapshot, catalog, read)
    case = tools.case_facts()
    capacity = tools.facility_snapshot("credit_risk")
    gathered = {desk: tools.evidence_index(desk) for desk in DESK_TOPICS}
    policies = {
        desk: tools.policy_search(desk, topic, "NL", tools.as_of)
        for desk, topic in DESK_TOPICS.items()
    }
    return {
        desk: candidates(desk, case=case, capacity=capacity, sources=gathered[desk], policies=policies[desk])
        for desk in DESK_TOPICS
    }


def fixture_turn(**request):
    context = json.loads(request["messages"][-1]["content"])
    return ModelTurn("fixture", json.dumps({"summary": context["wordings"][0]}))


def packet_json(completion):
    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("Duplicate JSON field")
        return result

    if not isinstance(completion, str):
        raise ValueError("Expected a JSON packet")
    return json.loads(completion, object_pairs_hook=unique)


def run_agent(snapshot, catalog, *, run_id, mode, policy_version, send, authorize, report=None):
    budget = RunBudget()
    observations = []

    def result(status, packets=None, reason=None):
        return AnalysisResult(
            snapshot["case_id"], snapshot["revision"], run_id, mode, policy_version,
            status, packets, observations, budget.model_calls, budget.tool_reads, reason,
        )

    def read():
        budget.read()
        authorize()

    try:
        inputs = contexts(snapshot, catalog, read)
        packets = {}
        for desk, options in inputs.items():
            if report:
                report(desk, "started")
            # Bind figures and citations from bank records after the wording has been selected.
            context = {"desk": desk, "next_step": options[0]["suggested_next_step"],
                       "wordings": [option["summary"] for option in options]}
            request = {
                "case_ref": snapshot["case_id"], "revision": snapshot["revision"],
                "run_id": run_id, "task": f"draft_{desk}", "policy_version": policy_version,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                "tool_schema": (),
            }
            while True:
                authorize()
                budget.call()
                turn = send(**request, timeout=budget.remaining())
                observations.append({**turn.observation, "task": request["task"], "route": turn.route})
                budget.remaining()
                if turn.route != "unavailable" or not turn.transient or budget.retried:
                    break
                budget.retried = True
            if turn.route == "blocked":
                return result("analysis_refused", reason="brane_policy_refused")
            expected_routes = {"fixture"} if mode == "fixture" else {"direct", "pseudonymized", "local"}
            if turn.route not in expected_routes:
                return result("analysis_unavailable", reason="brane_unavailable")
            choice = packet_json(turn.completion)
            if not isinstance(choice, dict) or set(choice) != {"summary"} or choice["summary"] not in context["wordings"]:
                return result("analysis_invalid", reason="unverified_packet")
            packet = options[context["wordings"].index(choice["summary"])]
            packets[desk] = validate_draft(packet, options)
            if report:
                report(desk, "prepared")
        return result("prepared", packets)
    except BudgetExceeded:
        return result("analysis_unavailable", reason="run_budget_exhausted")
    except PermissionError:
        return result("analysis_unavailable", reason="case_or_evidence_unavailable")
    except (ValueError, KeyError, TypeError):
        return result("analysis_invalid", reason="unverified_packet")
