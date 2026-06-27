"""FastAPI application: OpenAI-compatible firewall proxy + dashboard API.

Endpoints
---------
POST /v1/chat/completions  drop-in OpenAI endpoint, inspected + enforced
GET  /v1/models            static model list (compat)
GET  /events               Server-Sent Events stream of firewall decisions
GET  /api/receipts         recent signed receipts
GET  /api/receipts/{id}    one receipt + signature verification
GET  /api/policy           active policy (for dashboard chips)
GET  /api/stats            allow / redact / block counters
POST /api/seed             emit a synthetic event (demo / dashboard test)
POST /api/reset            wipe stored receipts/events/usage (demo)
GET  /health               liveness
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from .config import get_settings
from .demo import run_scenarios
from .engine import Engine, validate_request
from .events import EventBus
from .groq_client import GroqClient
from .mission import SCENARIOS, run_mission
from .policy import load_policy
from .receipts import verify
from .schemas import Action, Event, Status
from .store import Store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    app.state.policy = load_policy(settings.policy_path)
    app.state.store = Store(settings.db_path)
    app.state.bus = EventBus()
    app.state.client = GroqClient(settings)
    app.state.engine = Engine(
        settings, app.state.policy, app.state.store, app.state.client, app.state.bus
    )
    try:
        yield
    finally:
        await app.state.client.aclose()


app = FastAPI(title="Agent Firewall", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo; tighten via settings.cors_origins in prod
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# core proxy
# --------------------------------------------------------------------------- #
@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    engine: Engine = request.app.state.engine
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON body"}, status_code=400)
    if not isinstance(payload, dict) or "messages" not in payload:
        return JSONResponse({"error": "missing 'messages'"}, status_code=400)
    try:
        validate_request(payload)  # enforce OpenAI-compatible schema before inspection
    except ValidationError as exc:
        return JSONResponse(
            {"error": "invalid_request", "detail": str(exc).splitlines()[0]}, status_code=400
        )

    payload["stream"] = False  # inspection needs the full completion
    session_id = request.headers.get("x-session-id") or f"sess-{uuid.uuid4().hex[:8]}"

    try:
        completion = await engine.handle(payload, session_id)
    except httpx.HTTPStatusError as exc:
        return JSONResponse(
            {"error": "upstream_error", "status": exc.response.status_code,
             "detail": exc.response.text[:500]},
            status_code=502,
        )
    except httpx.HTTPError as exc:
        return JSONResponse({"error": "upstream_unreachable", "detail": str(exc)}, status_code=502)
    return JSONResponse(completion, headers={"x-session-id": session_id})


@app.get("/v1/models")
async def models(request: Request) -> dict:
    s = request.app.state.settings
    ids = [s.victim_model, s.promptguard_model, s.safeguard_model]
    return {"object": "list", "data": [{"id": i, "object": "model"} for i in ids]}


# --------------------------------------------------------------------------- #
# dashboard API
# --------------------------------------------------------------------------- #
@app.get("/events")
async def events(request: Request) -> StreamingResponse:
    bus: EventBus = request.app.state.bus

    async def gen() -> AsyncIterator[bytes]:
        async with bus.subscribe() as q:
            yield b": connected\n\n"
            idle = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # short poll so a client disconnect is noticed within ~1s
                    event = await asyncio.wait_for(q.get(), timeout=1.0)
                except TimeoutError:
                    idle += 1
                    if idle >= 15:  # keepalive every ~15s
                        idle = 0
                        yield b": ping\n\n"
                    continue
                idle = 0
                yield f"data: {event.model_dump_json()}\n\n".encode()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/receipts")
async def list_receipts(request: Request, limit: int = 50) -> dict:
    store: Store = request.app.state.store
    return {"receipts": [r.model_dump(mode="json") for r in store.list_receipts(limit)]}


@app.get("/api/receipts/{receipt_id}")
async def get_receipt(request: Request, receipt_id: str) -> JSONResponse:
    store: Store = request.app.state.store
    settings = request.app.state.settings
    receipt = store.get_receipt(receipt_id)
    if receipt is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(
        {
            "receipt": receipt.model_dump(mode="json"),
            "verified": verify(receipt, settings.hmac_secret),
        }
    )


@app.get("/api/policy")
async def get_policy(request: Request) -> dict:
    policy = request.app.state.policy
    return policy.model_dump(mode="json")


@app.get("/api/stats")
async def stats(request: Request) -> dict:
    store: Store = request.app.state.store
    return store.stats()


@app.post("/api/seed")
async def seed(request: Request) -> dict:
    """Emit one synthetic blocked event — lets the dashboard be tested in isolation."""
    bus: EventBus = request.app.state.bus
    store: Store = request.app.state.store
    event = Event(
        id=f"evt-{uuid.uuid4().hex[:12]}",
        ts=datetime.now(UTC).isoformat(),
        session_id="demo",
        action=Action.BLOCK,
        status=Status.BLOCK,
        title="Blocked tool call",
        detail="egress to non-allowlisted host: attacker.com",
        rule="deterministic_rules",
    )
    store.save_event(event)
    await bus.publish(event)
    return {"ok": True, "event_id": event.id}


@app.post("/api/demo/run")
async def demo_run(request: Request) -> dict:
    """Run a deterministic spread of attacks through the engine (offline-safe)."""
    scenarios = await run_scenarios(request.app.state.engine)
    return {"ok": True, "scenarios": scenarios}


@app.get("/api/mission/scenarios")
async def mission_scenarios() -> dict:
    return {"scenarios": [{"id": k, **v} for k, v in SCENARIOS.items()]}


@app.post("/api/mission/run")
async def mission_run(request: Request) -> JSONResponse:
    engine: Engine = request.app.state.engine
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON body"}, status_code=400)

    preset = SCENARIOS.get(body.get("scenario", ""), {})
    task = body.get("task") or preset.get("task")
    document = body.get("document")
    if document is None:
        document = preset.get("document", "")
    if not task:
        return JSONResponse({"error": "missing 'task' or 'scenario'"}, status_code=400)

    try:
        result = await run_mission(
            engine,
            task=task,
            document=document,
            firewall_on=bool(body.get("firewall", True)),
            model=body.get("model"),
        )
    except httpx.HTTPStatusError as exc:
        return JSONResponse(
            {"error": "upstream_error", "status": exc.response.status_code,
             "detail": exc.response.text[:300]},
            status_code=502,
        )
    except httpx.HTTPError as exc:
        return JSONResponse({"error": "upstream_unreachable", "detail": str(exc)}, status_code=502)
    return JSONResponse(result)


@app.post("/api/reset")
async def reset(request: Request) -> dict:
    request.app.state.store.reset()
    return {"ok": True}


@app.get("/health")
async def health(request: Request) -> dict:
    s = request.app.state.settings
    return {
        "status": "ok",
        "groq_enabled": s.groq_enabled,
        "subscribers": request.app.state.bus.subscriber_count,
    }
