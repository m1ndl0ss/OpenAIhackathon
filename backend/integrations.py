"""Interfaces shared by Security, the case agent and the human workflow."""

from . import brane_client
from .agent.runtime import AnalysisResult, fixture_turn, run_agent


def is_assigned(principal, assignments):
    return bool(principal.get("id")) and assignments.get(principal["role"]) == principal["id"]


def analysis_ready(mode):
    if mode == "fixture":
        return True
    try:
        brane_client.live_run_config()
    except RuntimeError:
        return False
    return mode == "live"


def prepare_packets(snapshot, mode, *, run_id, authorize, report=None):
    from .workflow import source_catalog

    if mode == "fixture":
        version, send = snapshot["brane_policy_version"], fixture_turn
    elif mode == "live":
        try:
            _, _, version, _ = brane_client.live_run_config()
        except RuntimeError:
            return AnalysisResult(snapshot["case_id"], snapshot["revision"], run_id, mode, "unknown",
                                  "analysis_unavailable", None, [], 0, 0, "brane_not_configured")
        send = brane_client.send_turn
    else:
        raise ValueError("Unknown analysis mode")
    return run_agent(snapshot, source_catalog(snapshot), run_id=run_id, mode=mode,
                     policy_version=version, send=send, authorize=authorize, report=report)
