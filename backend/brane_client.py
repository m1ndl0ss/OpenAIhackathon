"""Server-side transport for the assigned AI-Z department and its approved policy."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from scripts.brane_client import ASSIGNED_BASE, USER_AGENT, NoRedirect, observed_outcome, policy_hash

from .agent.runtime import ModelTurn, permitted_turn

POLICY_VERSION = "hardened-v2"
POLICY_FILE = Path(__file__).resolve().parents[1] / "policy" / f"{POLICY_VERSION}.json"


def live_config():
    base = os.getenv("BRANE_BASE_URL", ASSIGNED_BASE).rstrip("/")
    if base != ASSIGNED_BASE:
        raise RuntimeError("BRANE_BASE_URL must be the assigned HTTPS API base.")
    token = os.getenv("BRANE_API_KEY") or os.getenv("BRANE_TOKEN")
    if not token:
        raise RuntimeError("Set BRANE_API_KEY to the AI-Z team credential.")
    return base, token


def live_run_config():
    base, token = live_config()
    version = os.getenv("BRANE_POLICY_VERSION", "")
    model = os.getenv("BRANE_MODEL", "")
    if version != POLICY_VERSION or not re.fullmatch(r"[A-Za-z0-9_./:-]{1,100}", model):
        raise RuntimeError(f"Set the assigned BRANE model and BRANE_POLICY_VERSION={POLICY_VERSION}.")
    return base, token, version, model


def headers_for(token):
    return {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT, "Accept": "application/json"}


def read_json(response, limit):
    body = response.read(limit + 1)
    if len(body) > limit:
        raise ValueError("Response exceeds the allowed size")
    return json.loads(body)


def check_policy(timeout=10):
    base, token, _, _ = live_run_config()
    request = Request(base + "/policy", headers=headers_for(token))
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError("The team policy could not be verified.")
            policy = read_json(response, 262_144)
        expected = policy_hash(json.loads(POLICY_FILE.read_text(encoding="utf-8")))
        observed = policy_hash(policy)
        rules = policy["semanticCategories"]
        if observed != expected or any(rule.get("enabled") is False for rule in rules):
            raise RuntimeError("Deployed BRANE policy differs from the committed policy.")
        return observed
    except HTTPError as error:
        with error:
            raise RuntimeError(f"BRANE policy check returned HTTP {error.code}.") from None
    except (AttributeError, KeyError, TypeError, ValueError, URLError, TimeoutError, OSError):
        raise RuntimeError("BRANE policy unavailable or unrecognised.") from None


def send_turn(*, case_ref, revision, run_id, task, policy_version, messages, tool_schema, timeout):
    if tool_schema or not permitted_turn(task, messages):
        return ModelTurn("unavailable", observation={"stage": "outbound_projection"})
    deadline = monotonic() + timeout
    try:
        base, token, configured_policy, model = live_run_config()
        if policy_version != configured_policy:
            return ModelTurn("unavailable")
        verified_hash = check_policy(timeout=min(timeout, 10))
    except RuntimeError:
        return ModelTurn("unavailable", observation={"stage": "policy_check"})

    remaining = deadline - monotonic()
    if remaining <= 0:
        return ModelTurn("unavailable", observation={"stage": "policy_check", "policy_hash": verified_hash})
    request = Request(
        base + "/chat/completions",
        data=json.dumps({"model": model, "messages": messages, "stream": False}).encode("utf-8"),
        headers={**headers_for(token), "Content-Type": "application/json"}, method="POST",
    )
    audit = {"policy_hash": verified_hash, "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        with build_opener(NoRedirect()).open(request, timeout=min(remaining, 20)) as response:
            audit.update(observation_for(response.headers, response.status))
            if response.status != 200:
                return ModelTurn("unavailable", observation=audit)
            route = observed_outcome(response.status, audit)
            reported_version = audit["reported_policy_version"]
            if route == "unavailable" or (reported_version and reported_version != configured_policy):
                return ModelTurn("unavailable", observation=audit)
            content = read_json(response, 65_536)
            message = content["choices"][0]["message"]
            completion = None if message.get("tool_calls") else message.get("content")
            audit["provider_request_id"] = audit["provider_request_id"] or safe_id(content.get("id"))
            audit["model"] = audit["model"] or safe_id(content.get("model"))
            usage = content.get("usage")
            usage = usage if isinstance(usage, dict) else {}
            audit["usage"] = {
                key: value if type(value := usage.get(key)) is int and value >= 0 else None
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            }
            return ModelTurn(route, completion, audit)
    except HTTPError as error:
        with error:
            audit.update(observation_for(error.headers, error.code))
            if observed_outcome(error.code, audit) == "blocked":
                return ModelTurn("blocked", observation=audit)
            return ModelTurn("unavailable", observation=audit, transient=error.code in (429, 502, 503, 504))
    except (URLError, TimeoutError, OSError):
        return ModelTurn("unavailable", observation=audit, transient=True)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return ModelTurn("unavailable", observation=audit)


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_./:,> -]{1,512}", value):
        return None
    if any(token and token in value for token in (os.getenv("BRANE_API_KEY"), os.getenv("BRANE_TOKEN"))):
        return None
    return value


def observation_for(headers, status):
    fields = {
        "routed_to": "Routed-To", "action": "Action", "redacted": "Redacted", "model": "Model-Resolved",
        "redaction_classes": "Placeholder-Types", "pii_types": "Pii-Types", "pii_detected": "Pii-Detected",
        "allowed_types": "Allowed-Types", "semantic_matches": "Semantic-Matches", "local_cause": "Local-Cause",
        "rule_id": "Refused-By", "policy_triggers": "Policy-Triggers", "lane": "Lane", "log_ref": "Log-Ref",
        "reported_policy_version": "Policy-Version",
    }
    return {
        **{key: safe_id(headers.get("X-Brane-" + suffix)) for key, suffix in fields.items()},
        "http_status": status, "provider_request_id": safe_id(headers.get("X-Request-ID")),
    }
