#!/usr/bin/env python3
"""
Shared BRANE client for team Redwood's security workstream.

Standard library only, matching the starter kit. Three rules this module enforces
so the rest of the scripts cannot break them:

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
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
USER_AGENT = "Redwood-Security-Harness/1.0 (MAIN-Summit-2026)"

# The one endpoint we are allowed to talk to. Anything else is a bug, not a fallback.
ALLOWED_HOST = "brane.ai-z.io"

# Production is https-only. scripts/check_failure_test.py temporarily moves this (and
# ALLOWED_HOST) so it can point the pinned client at a dead address or a local stub and
# observe what happens. The pin stays ON throughout; only its target changes. Nothing
# reads these from the environment, so no deployment can relax them by accident.
ALLOWED_SCHEME = "https"


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
        if key and key not in os.environ:
            os.environ[key] = value


def base_url() -> str:
    url = (os.environ.get("BRANE_BASE_URL") or "").rstrip("/")
    if not url:
        raise BraneConfigError("BRANE_BASE_URL is not set. Copy .env.example to .env.")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != ALLOWED_SCHEME:
        raise BraneConfigError(
            f"BRANE_BASE_URL must be {ALLOWED_SCHEME}, got scheme '{parsed.scheme}'.")
    if parsed.hostname != ALLOWED_HOST:
        raise BraneConfigError(
            f"BRANE_BASE_URL host must be {ALLOWED_HOST}, got '{parsed.hostname}'. "
            "No other provider may be called from this harness."
        )
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
    """Safe, non-reversible description of the loaded key, for run logs."""
    key = api_key()
    return f"prefix={key[:9]}... length={len(key)}"


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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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
    return {k: v for k, v in sorted(headers.items()) if k.startswith("x-brane-")}


# --------------------------------------------------------------------------------------
# Reference implementation of docs/brane_adapter_contract.md §3.
#
# request() above is transport only: it hands back whatever came off the wire. That is
# deliberate, because the evidence harness needs the raw observation. It is NOT safe to
# hand to an agent, and check_failure_test.py proves why: a 200 carrying a completion but
# no X-Brane-Routed-To is indistinguishable from a governed answer at the transport layer.
# Classification has to happen above it, so here it is, once, for everyone to reuse.
# --------------------------------------------------------------------------------------
OUTCOMES = ("direct", "pseudonymized", "local", "blocked", "unavailable")


def classify_outcome(status: str, headers: Dict[str, str]) -> str:
    """
    Map an observation onto exactly one of the five normalised outcomes.

    An HTTP 200 with no X-Brane-Routed-To is `unavailable`, never `direct`: a response
    we cannot attribute to a policy decision is not a permitted route.
    """
    h = brane_headers(headers)
    routed = h.get("x-brane-routed-to")

    if status == "422" or routed == "refused":
        return "blocked"
    if status != "200":
        return "unavailable"
    if routed is None:
        return "unavailable"
    if routed == "local":
        return "local"
    if routed == "cloud":
        return "pseudonymized" if h.get("x-brane-redacted") == "true" else "direct"
    return "unavailable"


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
    answer = None
    if isinstance(body, dict) and body.get("choices"):
        answer = (body["choices"][0].get("message") or {}).get("content")

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
