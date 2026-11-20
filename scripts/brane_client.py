#!/usr/bin/env python3
"""
Shared BRANE configuration, transport and verdict handling for Redwood.

The client uses the standard library and enforces three transport guarantees:

  1. Every request goes to BRANE_BASE_URL. There is no fallback host, no direct
     provider call and no retry against a different endpoint.
  2. The API key is read from .env into memory only. It is never printed, never
     logged and never written to a file: scrub() strips it from anything on its
     way to disk or stdout.
  3. HTTP errors (notably the 422 policy refusals we want as evidence) are
     returned as ordinary results with their X-Brane-* headers intact, not
     raised away.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
USER_AGENT = "Redwood-Security-Harness/1.0 (MAIN-Summit-2026)"

# The one endpoint we are allowed to talk to. Anything else is a bug, not a fallback.
ALLOWED_HOST = "brane.ai-z.io"
ASSIGNED_BASE = f"https://{ALLOWED_HOST}/api/v1"
ENV_KEYS = {"BRANE_BASE_URL", "BRANE_API_KEY", "BRANE_TOKEN", "BRANE_MODEL", "BRANE_POLICY_VERSION", "TEAM_BUILD"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class BraneConfigError(RuntimeError):
    """Configuration problem. Message never contains the key."""


def load_env(path: Path = ENV_PATH) -> None:
    """Load .env into os.environ without overriding anything already set."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in ENV_KEYS and key not in os.environ:
            os.environ[key] = value


def base_url() -> str:
    url = (os.environ.get("BRANE_BASE_URL") or "").rstrip("/")
    if not url:
        raise BraneConfigError("BRANE_BASE_URL is not set. Copy .env.example to .env.")
    if url != ASSIGNED_BASE:
        raise BraneConfigError("BRANE_BASE_URL must be the assigned HTTPS API base.")
    return url


def api_key() -> str:
    key = (os.environ.get("BRANE_API_KEY") or "").strip()
    if not key:
        raise BraneConfigError(
            "BRANE_API_KEY is empty. Paste the team key into .env (never into a script, "
            "an evidence file or the terminal)."
        )
    return key


def key_fingerprint() -> str:
    """Confirm configuration without disclosing any fragment of the credential."""
    api_key()
    return "configured"


def team_build() -> str:
    return os.environ.get("TEAM_BUILD", "Redwood / policy-v1")


def scrub(value: Any) -> Any:
    """Remove the API key from anything that is about to be written or printed."""
    secret = (os.environ.get("BRANE_API_KEY") or "").strip()
    if isinstance(value, str):
        return value.replace(secret, "<BRANE_API_KEY_REDACTED>") if secret else value
    if isinstance(value, dict):
        out: Dict[Any, Any] = {}
        for k, v in value.items():
            if str(k).lower() in ("authorization", "brane_api_key", "api_key", "x-api-key"):
                out[k] = "<REDACTED>"
            else:
                out[k] = scrub(v)
        return out
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def _headers(auth: bool, json_body: bool) -> Dict[str, str]:
    h = {"User-Agent": USER_AGENT}
    if auth:
        h["Authorization"] = f"Bearer {api_key()}"
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    auth: bool = True,
    timeout: float = 60.0,
) -> Tuple[str, Dict[str, str], Any, str]:
    """
    Call BRANE. Returns (status, headers, parsed_body_or_None, raw_text).

    status is the HTTP code as a string, or "ERROR" when the request never
    completed. Non-2xx responses come back normally with their headers so a 422
    refusal can be recorded as evidence. Nothing is retried elsewhere.
    """
    url = f"{base_url()}/{path.lstrip('/')}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(auth, body is not None), method=method)

    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as resp:
            status = str(resp.status)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        status = str(err.code)
        headers = {k.lower(): v for k, v in err.headers.items()} if err.headers else {}
        raw = err.read().decode("utf-8", errors="replace")
    except Exception as exc:  # network failure, timeout, DNS, TLS
        return "ERROR", {}, None, f"{type(exc).__name__}: {exc}"

    try:
        parsed = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError:
        parsed = None
    return status, headers, parsed, raw


def brane_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Every X-Brane-* header, lowercased keys, in sorted order."""
    return {k.lower(): v for k, v in sorted(headers.items()) if k.lower().startswith("x-brane-")}


# --------------------------------------------------------------------------------------
# Routing outcomes documented in docs/brane_adapter_contract.md.
#
# request() above is transport only: it hands back whatever came off the wire. That is
# deliberate, because the evidence harness needs the raw observation. It is NOT safe to
# hand to an agent, and check_failure_test.py proves why: a 200 carrying a completion but
# no X-Brane-Routed-To is indistinguishable from a governed answer at the transport layer.
# Classification has to happen above it, so here it is, once, for everyone to reuse.
# --------------------------------------------------------------------------------------
OUTCOMES = ("direct", "pseudonymized", "local", "blocked", "unavailable")


def observed_outcome(status, observation) -> str:
    """Classify the firewall verdict recorded by the staff API and the security runner."""
    route = observation.get("routed_to"), observation.get("action")
    if str(status) == "422" and route == ("refused", "refuse"):
        return "blocked"
    if str(status) != "200":
        return "unavailable"
    if route == ("cloud", "allow") and observation.get("redacted") == "false":
        return "direct"
    if route == ("cloud", "placeholder") and observation.get("redacted") == "true" and observation.get("redaction_classes"):
        return "pseudonymized"
    if route == ("local", "local") and (observation.get("model") or "").startswith("vllm:"):
        return "local"
    return "unavailable"


def classify_outcome(status: str, headers: Dict[str, str]) -> str:
    """
    Map an observation onto exactly one of the five normalised outcomes.

    An HTTP 200 with no X-Brane-Routed-To is `unavailable`, never `direct`: a response
    we cannot attribute to a policy decision is not a permitted route.
    """
    h = brane_headers(headers)
    return observed_outcome(status, {
        "routed_to": h.get("x-brane-routed-to"), "action": h.get("x-brane-action"),
        "redacted": h.get("x-brane-redacted"), "redaction_classes": h.get("x-brane-placeholder-types"),
        "model": h.get("x-brane-model-resolved"),
    })


def call_governed(prompt: str, timeout: float = 60.0, system: Optional[str] = None) -> Dict[str, Any]:
    """
    One governed model turn. Returns:

        {"outcome": one of OUTCOMES,
         "answer":  the model text, or None whenever the outcome is not a usable answer,
         "status":  HTTP status as a string, or "ERROR",
         "headers": every X-Brane-* header observed,
         "reason":  short safe reason for a non-answer outcome}

    `answer` is None for `blocked` and `unavailable`. That is the whole point: an
    unverified completion must not reach a caller who might reason over it.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    status, headers, body, raw = request(
        "POST", "/chat/completions", {"model": "auto", "messages": messages}, timeout=timeout
    )
    outcome = classify_outcome(status, headers)
    choices = body.get("choices") if isinstance(body, dict) else None
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    message = choice.get("message")
    answer = message.get("content") if isinstance(message, dict) and not message.get("tool_calls") else None
    if not isinstance(answer, str) or not answer.strip():
        answer = None
        if outcome != "blocked":
            outcome = "unavailable"

    if outcome in ("blocked", "unavailable"):
        reason = {
            "blocked": f"refused by policy ({brane_headers(headers).get('x-brane-refused-by', 'rule not reported')})",
            "unavailable": f"no policy decision observed (status={status})",
        }[outcome]
        return {"outcome": outcome, "answer": None, "status": status,
                "headers": brane_headers(headers), "reason": scrub(reason),
                "discarded_answer_chars": len(answer or "")}
    return {"outcome": outcome, "answer": answer, "status": status,
            "headers": brane_headers(headers), "reason": ""}


def call_raw(prompt: str, timeout: float = 60.0, system: Optional[str] = None) -> Dict[str, Any]:
    """
    Transport-only call in the same shape as call_governed, with NO classification and
    no answer suppression. Exists so check_failure_test.py can measure the difference
    between a transport and an adapter rather than assert it.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    status, headers, body, raw = request(
        "POST", "/chat/completions", {"model": "auto", "messages": messages}, timeout=timeout
    )
    answer = None
    if isinstance(body, dict) and body.get("choices"):
        answer = (body["choices"][0].get("message") or {}).get("content")
    elif status == "ERROR":
        answer = None
    return {"outcome": None, "answer": answer, "status": status,
            "headers": brane_headers(headers), "reason": ""}


def write_json(path: Path, payload: Any) -> None:
    """Write scrubbed JSON, creating parents. Idempotent: same input, same file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(scrub(payload), indent=2, ensure_ascii=False, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


# Fields PUT /policy accepts. Everything else GET returns (team, departmentId,
# summary, updatedAt, availableActions, catalogEndpoint, testEndpoint) is
# server-owned and must not be sent back.
WRITABLE_POLICY_FIELDS = ("routingMode", "piiSensitivity", "categories", "semanticCategories")


def writable_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    """The subset of a GET /policy body that PUT /policy accepts."""
    return {k: policy[k] for k in WRITABLE_POLICY_FIELDS if k in policy}


# The semantic-rule fields we author. BRANE adds `id` (a fresh UUID per rule) and
# `enabled` on storage. Hashing those would make the hash unreproducible from the
# policy file and would change on every re-create, so the canonical form projects
# onto these fields only. `enabled: false` is caught as drift by
# apply_policy.diff_policy instead, which is where a disabled rule must be noticed.
SEMANTIC_AUTHORED_FIELDS = ("code", "name", "description", "keywords", "legalBasis", "action")


def canonical_policy_text(policy: Dict[str, Any]) -> str:
    """
    Stable text form of the writable policy, for hashing and comparison.

    Identical for a policy file and for the same policy read back from BRANE:
    category order, semantic-rule order and server-assigned rule fields must not
    change the hash.
    """
    doc = dict(writable_policy(policy))
    semantic = doc.get("semanticCategories") or []
    if isinstance(semantic, list):
        doc["semanticCategories"] = sorted(
            (
                {k: s[k] for k in SEMANTIC_AUTHORED_FIELDS if k in s}
                for s in semantic
                if isinstance(s, dict)
            ),
            key=lambda s: str(s.get("code", "")),
        )
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def policy_hash(policy: Dict[str, Any]) -> str:
    """sha256 of the writable policy. Goes into every evidence row."""
    import hashlib

    return "sha256:" + hashlib.sha256(canonical_policy_text(policy).encode("utf-8")).hexdigest()[:32]


def rel(path: Path) -> str:
    """Repo-relative path for logs, tolerant of relative and absolute input."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def utc_stamp() -> str:
    """UTC timestamp for evidence filenames and rows: 20261120T143000Z."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
