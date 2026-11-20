"""Serve one visitor's synthetic case using the real staff workflow.

Vercel requests may land on different instances. The browser carries a signed
fixture database between calls. Only this service can produce an accepted
snapshot. Each request opens its own temporary database and runs in fixture mode.
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
import tempfile
import zlib
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import demo
from .main import PREFIX, create_app

MAX_DATABASE = 4 * 1024 * 1024
MAX_WORKSPACE = 640_000
MAX_REQUEST = MAX_WORKSPACE + 32_768
WORKSPACE_VERSION = b"redwood-public-fixture-v1:"
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class DemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str = Field(max_length=220, pattern=r"^/[A-Za-z0-9_/-]+$")
    workspace: str | None = Field(default=None, max_length=MAX_WORKSPACE)
    desk_token: str | None = Field(default=None, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    action_key: str | None = Field(default=None, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    body: dict | None = None


@lru_cache(maxsize=1)
def signing_key():
    # A configured key preserves demo tabs across redeploys. Otherwise the
    # Vercel build supplies a private per-build key alongside the function.
    key = os.environ.get("REDWOOD_DEMO_SIGNING_KEY")
    if key is None:
        path = Path(__file__).with_name("_public_demo.key")
        key = path.read_text().strip() if path.is_file() else ""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", key):
        raise HTTPException(503, "The public demo needs its server build key.")
    return bytes.fromhex(key)


def pack_workspace(path, visitor, key):
    if path.stat().st_size > MAX_DATABASE:
        raise HTTPException(413, "This demo tab is full. Start a new tab for another case.")
    packed = zlib.compress(path.read_bytes(), level=3)
    payload = visitor + packed
    signature = hmac.digest(key, WORKSPACE_VERSION + payload, hashlib.sha256)
    token = base64.urlsafe_b64encode(signature + payload).decode("ascii")
    if len(token) > MAX_WORKSPACE:
        raise HTTPException(413, "This demo tab is full. Start a new tab for another case.")
    return token


def restore_workspace(path, token, key):
    if token is None:
        return secrets.token_bytes(16)
    try:
        raw = base64.b64decode(token, altchars=b"-_", validate=True)
    except ValueError:
        raw = b""
    signature, payload = raw[:32], raw[32:]
    if len(payload) <= 16 or not hmac.compare_digest(signature, hmac.digest(key, WORKSPACE_VERSION + payload, "sha256")):
        raise HTTPException(410, "This demo workspace has expired. Reopen the desk picker to start a fresh case.")
    # Verify the signature before decompressing or handing any bytes to SQLite.
    db = zlib.decompressobj().decompress(payload[16:], MAX_DATABASE + 1)
    if len(db) > MAX_DATABASE:
        raise HTTPException(413, "The stored workspace exceeds the demo limit.")
    path.write_bytes(db)
    return payload[:16]


def sandbox(path, visitor, key):
    people = {**demo.make_principals(), **demo.make_principals(specialists=True)}
    bank = create_app(path, people, mode="fixture")
    bank.state.visitor_fixture = True
    bank.state.demo_sessions = {}
    for person in people.values():
        token = hmac.digest(key, b"demo-desk:" + visitor + person["id"].encode(), "sha256").hex()
        bank.state.demo_sessions[person["id"]] = (token, person)
    return bank


@app.post("/api/demo")
async def exchange(request: Request):
    # Limit the envelope before decoding JSON. Signed state stays in the HTTP
    # body and never appears in URLs, cookies or server access logs.
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_REQUEST:
            return JSONResponse({"message": "This demo request is too large."}, 413)
        content.extend(chunk)
    try:
        command = DemoRequest.model_validate_json(bytes(content))
    except ValueError:
        return JSONResponse({"message": "Check the submitted demo request."}, 422)
    if "//" in command.path or command.body is not None and command.body.get("mode") == "live":
        return JSONResponse({"message": "Public requests use synthetic fixture mode."}, 422)
    headers = {}
    if command.desk_token:
        headers["Authorization"] = "Bearer " + command.desk_token
    if command.action_key:
        headers["Idempotency-Key"] = command.action_key
    key = signing_key()
    with tempfile.TemporaryDirectory(prefix="redwood-visitor-") as folder:
        path = Path(folder) / "case.sqlite3"
        visitor = restore_workspace(path, command.workspace, key)
        bank = sandbox(path, visitor, key)
        # ASGI transport dispatches in this process. There is no network proxy.
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=bank), base_url="https://demo.invalid") as client:
            if command.body is None:
                result = await client.get(PREFIX + command.path, headers=headers)
            else:
                result = await client.post(PREFIX + command.path, headers=headers, json=command.body)
        reply = {"status": result.status_code, "data": result.json()}
        if command.workspace is None or command.body is not None:
            reply["workspace"] = pack_workspace(path, visitor, key)
        return JSONResponse(reply, headers={"Cache-Control": "private, no-store"})


@app.exception_handler(HTTPException)
async def demo_error(_request, error):
    return JSONResponse({"message": error.detail}, error.status_code, headers={"Cache-Control": "no-store"})
