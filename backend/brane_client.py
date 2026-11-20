"""Server-side BRANE policy probe and governed model transport."""

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .agent.runtime import ModelTurn


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def live_config():
    base_url = os.getenv("BRANE_BASE_URL", "https://brane.ai-z.io/api/v1").rstrip("/")
    address = urlsplit(base_url)
    if (address.scheme != "https" or not address.hostname or address.username is not None
            or address.password is not None or address.query or address.fragment):
        raise RuntimeError("BRANE_BASE_URL must be the assigned HTTPS API base URL.")
    token = os.getenv("BRANE_API_KEY") or os.getenv("BRANE_TOKEN")
    if not token:
        raise RuntimeError("Set BRANE_API_KEY to the AI-Z team credential before running the live check.")
    return base_url, token


def check_policy():
    base_url, token = live_config()
    request = Request(base_url + "/policy", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with build_opener(_NoRedirect()).open(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError("BRANE did not return the team policy.")
            policy = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"BRANE policy check returned HTTP {error.code}.") from None
    except (ValueError, URLError, TimeoutError, OSError):
        raise RuntimeError("BRANE policy check unavailable. Check the assigned host and network.") from None
    if not isinstance(policy, dict) or not any(field in policy for field in ("categories", "summary", "routingMode")):
        raise RuntimeError("BRANE response did not contain a recognised team policy.")


def live_run_config():
    base, token = live_config()
    policy = os.getenv("BRANE_POLICY_VERSION", "")
    model = os.getenv("BRANE_MODEL", "")
    if not all(re.fullmatch(r"[A-Za-z0-9_./:-]{1,100}", value) for value in (policy, model)):
        raise RuntimeError("Set the assigned BRANE model and configured policy version for live analysis.")
    return base, token, policy, model


def send_turn(*, case_ref, revision, run_id, task, policy_version, messages, tool_schema, timeout):
    try:
        base, token, configured_policy, model = live_run_config()
    except RuntimeError:
        return ModelTurn("unavailable")
    if policy_version != configured_policy or tool_schema:
        return ModelTurn("unavailable")

    request = Request(
        base + "/chat/completions",
        data=json.dumps({"model": model, "messages": messages, "stream": False}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=min(timeout, 15)) as response:
            if response.status != 200:
                return ModelTurn("unavailable")
            route = {
                ("cloud", "allow"): "direct",
                ("cloud", "placeholder"): "pseudonymized",
                ("local", "local"): "local",
            }.get((response.headers.get("X-Brane-Routed-To"), response.headers.get("X-Brane-Action")))
            reported_version = response.headers.get("X-Brane-Policy-Version")
            if (not route or route == "pseudonymized" and response.headers.get("X-Brane-Redacted") != "true"
                    or reported_version and reported_version != configured_policy):
                return ModelTurn("unavailable")
            data = response.read(65_537)
            if len(data) > 65_536:
                return ModelTurn("unavailable")
            content = json.loads(data)
            message = content["choices"][0]["message"]
            completion = None if message.get("tool_calls") else message.get("content")
            observation = observation_for(response.headers, content, reported_version)
            return ModelTurn(route, completion, observation)
    except HTTPError as error:
        with error:
            if error.code == 422 and (
                error.headers.get("X-Brane-Action") == "refuse"
                or error.headers.get("X-Brane-Routed-To") == "refused"
            ):
                return ModelTurn("blocked", observation=observation_for(error.headers, {}))
            return ModelTurn("unavailable", transient=error.code in (429, 502, 503, 504))
    except (URLError, TimeoutError, OSError):
        return ModelTurn("unavailable", transient=True)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return ModelTurn("unavailable")


def observation_for(headers, content, reported_version=None):
    def safe_id(value):
        return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_./:,-]{1,128}", value) else None

    usage = content.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    return {
        "provider_request_id": safe_id(headers.get("X-Request-ID") or content.get("id")),
        "rule_id": safe_id(headers.get("X-Brane-Refused-By")),
        "model": safe_id(headers.get("X-Brane-Model-Resolved") or content.get("model")),
        "redaction_classes": safe_id(headers.get("X-Brane-Placeholder-Types")),
        "log_ref": safe_id(headers.get("X-Brane-Log-Ref")),
        "reported_policy_version": safe_id(reported_version),
        "usage": {
            k: usage.get(k) if type(usage.get(k)) is int and usage[k] >= 0 else None
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
    }
