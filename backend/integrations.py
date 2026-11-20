"""Interfaces shared by Security, the case agent and the human workflow."""

from backend.agent.packets import fixture_packets


def is_assigned(principal, assignments):
    return bool(principal.get("id")) and assignments.get(principal["role"]) == principal["id"]


def prepare_packets(snapshot, mode):
    if mode == "fixture":
        return fixture_packets(snapshot)
    # Matvei and Tasos connect governed model calls and validated desk output here.
    # Until then a live run has no output eligible for human sign-off.
    raise RuntimeError("Live case analysis is unavailable.")
