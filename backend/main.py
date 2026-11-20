"""Staff API for the synthetic corporate letter-of-credit case."""

import json
import os
import secrets
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import integrations
from .demo import ROOT, settings
from .store import DESKS, ROLES, canonical, digest, event, grouped_assignments, identifier, initialize
from .store import insert_case, now, snapshot, transaction
from .workflow import (
    COMPLIANCE_REPLY,
    Problem,
    add_invoice,
    conflict,
    create_request,
    decide,
    detail,
    issue,
    on_version,
    visible_run_analysis,
)
from .workflow import record, require_open, require_role, review, seal, unavailable

PREFIX = "/v2/trade"
CASES = PREFIX + "/cases"
CASE = CASES + "/{case_id}"
Desk = Literal["coverage", "trade_finance", "credit_risk", "compliance", "final_officer", "operations"]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class Intake(Body):
    fixture_id: Literal[
        "LC-DEMO-001", "LC-COMPLETE", "LC-INSUFFICIENT", "LC-OVER-MANDATE",
        "LC-EXPIRED-FACILITY", "LC-INVALID-FACILITY",
    ]
    customer_ref: str = Field(min_length=1, max_length=80)
    facility_ref: str = Field(min_length=1, max_length=80)
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    expiry: str = Field(max_length=10)
    instrument: Literal["import_documentary_credit"]


class Revision(Body):
    revision: int = Field(ge=1)


class Run(Revision):
    mode: Literal["fixture", "live"]


class Signing(Revision):
    packet_hash: str = Field(pattern="^[0-9a-f]{64}$")


class Review(Signing):
    disposition: Literal["clear", "hold"]
    reason: str = Field(min_length=10, max_length=2000)
    reason_code: str = Field(min_length=1, max_length=40)
    expected_review_event_id: Optional[str] = Field(default=None, max_length=80)
    request_to: Optional[Desk] = None
    required_evidence: Optional[Literal["supplier_invoice"]] = None
    resolves_hold_ids: list[str] = Field(default_factory=list, max_length=3)
    evidence_ref: Optional[str] = Field(default=None, max_length=80)


class Question(Revision):
    to_desk: Desk
    question: str = Field(min_length=10, max_length=2000)


class Reply(Revision):
    reply: str = Field(min_length=10, max_length=2000)


class Invoice(Body):
    expected_revision: int = Field(ge=1)
    fixture_document_id: str = Field(min_length=1, max_length=80)
    request_id: Optional[str] = Field(default=None, max_length=80)
    note: str = Field(default="Supplier invoice attached for review.", min_length=10, max_length=2000)


class Decision(Signing):
    decision: Literal["approve", "decline", "refer"]
    reason: str = Field(min_length=10, max_length=2000)


def authenticated(request: Request, authorization: Optional[str] = Header(default=None)):
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() == "bearer" and supplied.isascii():
        for token, actor in request.app.state.principals.items():
            if secrets.compare_digest(token, supplied):
                return actor
    raise Problem(401, "unauthenticated", "Sign in with a valid staff session.")


def retry_key(idempotency_key: Optional[str] = Header(default=None)):
    if not idempotency_key or not 1 <= len(idempotency_key) <= 128 or not idempotency_key.isprintable():
        raise Problem(422, "idempotency_key_required", "Provide an Idempotency-Key for this action.")
    return idempotency_key


def finish_run(path, case_id, run_id, actor):
    with transaction(path) as db:
        r, s = record(db, case_id, actor)
        run = dict(db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())
    def authorize():
        try:
            with transaction(path) as db:
                _, active = record(db, case_id, actor)
                if active["revision"] == run["revision"]:
                    return
        except Problem:
            pass
        raise PermissionError("Case or revision is no longer available")

    result = None
    if r["revision"] == run["revision"] and not r["packet_hash"]:
        try:
            result = integrations.prepare_packets(s, run["mode"], run_id=run_id, authorize=authorize)
        except Exception:
            # Provider errors may contain restricted payloads. Persist only a safe status.
            pass
    with transaction(path, write=True) as db:
        r, current = record(db, case_id, actor)
        if r["packet_hash"] or current["revision"] != run["revision"]:
            status = "superseded"
        elif result is None:
            status = "analysis_unavailable"
        elif (result.case_ref, result.revision, result.run_id, result.mode) != (
            case_id, current["revision"], run_id, run["mode"]
        ):
            status = "analysis_invalid"
        elif result.status != "prepared":
            status = result.status
        else:
            try:
                seal(db, current, result.packets, {**run, "policy_version": result.policy_version})
                status = "sealed"
            except (ValueError, TypeError, KeyError):
                status = "analysis_invalid"
        if result is not None:
            report = {
                "policy_version": result.policy_version, "reason": result.reason,
                "model_calls": result.model_calls, "tool_reads": result.tool_reads,
                "observations": result.observations,
            }
            db.execute("INSERT INTO run_analysis VALUES(?,?)", (run_id, canonical(report)))
        db.execute("UPDATE runs SET status=?,ended_at=? WHERE run_id=?", (status, now(), run_id))
        event(
            db,
            {"case_id": case_id, "revision": run["revision"]},
            {"id": "case-agent", "role": "analysis"},
            "run." + status,
            run["mode"] + " · " + run_id,
        )


def mutate(request, actor, key, operation, case_id, body, handler, roles=ROLES, before_replay=None):
    """Apply a mutation and save its replay in the same write transaction."""
    path = request.app.state.path
    body_hash = digest(body.model_dump())
    args = (actor["id"], operation, case_id or "", key)
    try:
        with transaction(path, write=True) as db:
            r, s = record(db, case_id, actor) if case_id else (None, None)
            require_role(actor, roles)
            if isinstance(body, Signing) and r["packet_hash"] and r["mode"] != request.app.state.mode:
                conflict("mode_mismatch", "This packet belongs to a different analysis mode.")
            if isinstance(body, Run) and body.mode != request.app.state.mode:
                conflict("mode_mismatch", "Use the analysis mode configured for this deployment.")
            if before_replay:
                before_replay(db, r, s)
            prior = db.execute(
                "SELECT * FROM retries WHERE principal=? AND operation=? AND resource=? AND key=?", args
            ).fetchone()
            if prior:
                if prior["body_hash"] != body_hash:
                    conflict("conflicting_replay", "This action key was already used with different inputs.")
                return JSONResponse(json.loads(prior["response"]), prior["status"])
            status, response = handler(db, r, s)
            db.execute(
                "INSERT INTO retries VALUES(?,?,?,?,?,?,?)", (*args, body_hash, status, canonical(response))
            )
            return JSONResponse(response, status)
    except Problem as problem:
        if case_id and problem.status in (403, 409):
            with transaction(path, write=True) as db:
                _, s = record(db, case_id, actor)
                event(db, s, actor, "action.denied", problem.code)
        raise


def create_app(db_path=None, principals=None, *, mode=None):
    if (db_path is None) != (principals is None):
        raise ValueError("Provide both a database path and staff configuration")

    def configure(app, path, people):
        deployment_mode = mode if mode is not None else os.getenv("CLEARANCE_MODE", "fixture")
        if deployment_mode not in ("fixture", "live"):
            raise ValueError("CLEARANCE_MODE must be fixture or live.")
        if deployment_mode == "live" and mode is None:
            from .brane_client import live_run_config

            live_run_config()
        app.state.mode = deployment_mode
        initialize(path, people)
        app.state.path, app.state.principals = path, people
        app.state.assignments = grouped_assignments(people)

    @asynccontextmanager
    async def lifespan(app):
        if not hasattr(app.state, "path"):
            configure(app, *settings())
        yield

    app = FastAPI(title="Clearance · staff case API", lifespan=lifespan)
    if db_path is not None:
        configure(app, db_path, principals)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = identifier("HTTP")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith(PREFIX):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Problem)
    async def handle_problem(request, problem):
        response = {"code": problem.code, "message": problem.message, "request_id": request.state.request_id}
        if problem.next_action:
            response["next_action"] = problem.next_action
        return JSONResponse(response, problem.status)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request, _error):
        return JSONResponse(
            {
                "code": "invalid_input",
                "message": "Check the fields for this action.",
                "request_id": request.state.request_id,
            },
            422,
        )

    @app.get(PREFIX + "/me")
    def me(request: Request, actor=Depends(authenticated)):
        mode = request.app.state.mode
        return {**actor, "configured_mode": mode, "analysis_available": integrations.analysis_ready(mode)}

    @app.get(CASES)
    def cases(request: Request, actor=Depends(authenticated)):
        fields = ("case_id", "customer_ref", "amount_minor", "currency", "revision", "status", "next_action")
        result = []
        with transaction(request.app.state.path) as db:
            for row in db.execute(
                "SELECT id,assignments FROM cases WHERE customer=? ORDER BY id", (actor["customer_ref"],)
            ):
                if integrations.is_assigned(actor, json.loads(row["assignments"])):
                    r, s = record(db, row["id"], actor)
                    view = detail(db, r, s, actor, request.app.state.mode)
                    result.append({k: view[k] for k in fields})
        return result

    @app.post(CASES)
    def open_case(request: Request, body: Intake, actor=Depends(authenticated), key=Depends(retry_key)):
        if body.customer_ref != actor["customer_ref"]:
            unavailable()

        def persist(db, _r, _s):
            s = snapshot(
                identifier("LC"), actor["customer_ref"], body.fixture_id != "LC-DEMO-001", body.fixture_id
            )
            expected = body.model_dump(exclude={"fixture_id"})
            if any(s[k] != v for k, v in expected.items()):
                raise Problem(
                    422, "intake_mismatch", "The intake must match its registered synthetic fixture."
                )
            insert_case(db, s, request.app.state.assignments[actor["customer_ref"]], actor)
            r, s = record(db, s["case_id"], actor)
            return 201, detail(db, r, s, actor, request.app.state.mode)

        return mutate(request, actor, key, "create", None, body, persist, ("coverage",))

    @app.get(CASE)
    def case(request: Request, case_id: str, actor=Depends(authenticated)):
        with transaction(request.app.state.path) as db:
            r, s = record(db, case_id, actor)
            return detail(db, r, s, actor, request.app.state.mode)

    @app.get(CASE + "/audit")
    def audit(request: Request, case_id: str, actor=Depends(authenticated)):
        with transaction(request.app.state.path) as db:
            record(db, case_id, actor)
            return [
                dict(e)
                for e in db.execute(
                    "SELECT * FROM audit WHERE case_id=? AND "
                    "(action!='action.denied' OR actor_id=?) ORDER BY sequence",
                    (case_id, actor["id"]),
                )
            ]

    @app.post(CASE + "/runs")
    def run(
        request: Request,
        case_id: str,
        body: Run,
        tasks: BackgroundTasks,
        actor=Depends(authenticated),
        key=Depends(retry_key),
    ):
        def persist(db, r, s):
            require_open(db, s)
            on_version(s, body.revision)
            if r["packet_hash"]:
                conflict("already_sealed", "This revision already has a sealed review packet.")
            run_id = identifier("RUN")
            db.execute(
                "INSERT INTO runs VALUES(?,?,?,?,?,?,NULL)",
                (run_id, case_id, s["revision"], body.mode, "pending", now()),
            )
            event(db, s, actor, "run.started", body.mode + " · " + run_id)
            tasks.add_task(finish_run, request.app.state.path, case_id, run_id, actor)
            return 202, {"run_id": run_id, "mode": body.mode, "revision": s["revision"], "status": "pending"}

        return mutate(request, actor, key, "run", case_id, body, persist, ("coverage", "final_officer"))

    @app.get(CASE + "/runs/{run_id}")
    def run_info(request: Request, case_id: str, run_id: str, actor=Depends(authenticated)):
        with transaction(request.app.state.path) as db:
            record(db, case_id, actor)
            result = db.execute(
                "SELECT * FROM runs WHERE case_id=? AND run_id=?", (case_id, run_id)
            ).fetchone()
            if not result:
                unavailable()
            return {**dict(result), "analysis": visible_run_analysis(db, run_id, actor["role"])}

    @app.post(CASE + "/requests")
    def ask(
        request: Request, case_id: str, body: Question, actor=Depends(authenticated), key=Depends(retry_key)
    ):
        def persist(db, r, s):
            require_open(db, s)
            on_version(s, body.revision)
            req_id = create_request(db, s, actor, body.to_desk, body.question)
            return 201, {"request_id": req_id, "revision": s["revision"]}

        return mutate(request, actor, key, "request", case_id, body, persist)

    @app.post(CASE + "/requests/{request_id}/replies")
    def answer(
        request: Request,
        case_id: str,
        request_id: str,
        body: Reply,
        actor=Depends(authenticated),
        key=Depends(retry_key),
    ):
        def entitled(db, r, s):
            if not db.execute(
                "SELECT 1 FROM requests WHERE case_id=? AND request_id=? AND to_desk=?",
                (case_id, request_id, actor["role"]),
            ).fetchone():
                unavailable()

        def persist(db, r, s):
            require_open(db, s)
            on_version(s, body.revision)
            if actor["role"] == "compliance" and body.reply != COMPLIANCE_REPLY:
                raise Problem(422, "restricted_text", "Choose the approved shareable Compliance reply.")
            updated = db.execute(
                "UPDATE requests SET status='answered',reply=?,answered_revision=? "
                "WHERE case_id=? AND request_id=? AND status='open'",
                (body.reply, s["revision"], case_id, request_id),
            )
            if not updated.rowcount:
                conflict("question_answered", "This question has already been answered.")
            event(db, s, actor, "request.answered", "The recipient answered a desk question.")
            return 200, {"request_id": request_id, "status": "answered", "revision": s["revision"]}

        return mutate(
            request, actor, key, "reply/" + request_id, case_id, body, persist, before_replay=entitled
        )

    @app.post(CASE + "/evidence")
    def evidence(
        request: Request, case_id: str, body: Invoice, actor=Depends(authenticated), key=Depends(retry_key)
    ):
        return mutate(
            request,
            actor,
            key,
            "evidence",
            case_id,
            body,
            lambda db, r, s: (201, add_invoice(db, r, s, actor, body)),
            ("coverage",),
        )

    @app.post(CASE + "/reviews/{desk}")
    def sign(
        request: Request,
        case_id: str,
        desk: str,
        body: Review,
        actor=Depends(authenticated),
        key=Depends(retry_key),
    ):
        roles = (desk,) if desk in DESKS else ()
        return mutate(
            request,
            actor,
            key,
            "review/" + desk,
            case_id,
            body,
            lambda db, r, s: (201, review(db, r, s, actor, body)),
            roles,
        )

    @app.post(CASE + "/decision")
    def decision(
        request: Request, case_id: str, body: Decision, actor=Depends(authenticated), key=Depends(retry_key)
    ):
        return mutate(
            request,
            actor,
            key,
            "decision",
            case_id,
            body,
            lambda db, r, s: (201, decide(db, r, s, actor, body)),
            ("final_officer",),
        )

    @app.post(CASE + "/issuance")
    def issuance(
        request: Request, case_id: str, body: Signing, actor=Depends(authenticated), key=Depends(retry_key)
    ):
        return mutate(
            request,
            actor,
            key,
            "issuance",
            case_id,
            body,
            lambda db, r, s: issue(db, r, s, actor, body),
            ("operations",),
        )

    dist = ROOT / "console" / "dist"
    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="console")
    return app


app = create_app()
