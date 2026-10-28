"""Local dashboard server: FastAPI, 127.0.0.1 only, per-launch token.

Token gates /api/* (header X-MLDoctor-Token or ?token= for SSE).
Script paths must resolve inside the allowed dir (default: cwd).
Pipeline always runs on MockClient here; no live calls from the dashboard.
"""
import asyncio
import json
import os
import queue
import secrets
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app(allowed_dir=None, token=None):
    allowed = os.path.realpath(allowed_dir or os.getcwd())
    app = FastAPI(title="MLDoctor")
    app.state.token = token or secrets.token_urlsafe(18)
    app.state.allowed_dir = allowed
    app.state.bus_queue = queue.Queue()
    app.state.summary = None
    app.state.running = False
    app.state.events = []

    def check_token(request):
        tok = request.headers.get("x-mldoctor-token") or request.query_params.get("token")
        if tok != app.state.token:
            raise HTTPException(401, "bad or missing token")

    def listener(ev):
        app.state.events.append(ev)
        app.state.bus_queue.put(ev)

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC, "index.html"))

    @app.get("/app.css")
    def css():
        return FileResponse(os.path.join(STATIC, "app.css"), media_type="text/css")

    @app.get("/app.js")
    def js():
        return FileResponse(os.path.join(STATIC, "app.js"), media_type="text/javascript")

    @app.get("/api/state")
    def state(request: Request):
        check_token(request)
        return {"running": app.state.running, "summary": app.state.summary,
                "events": app.state.events, "mock": True,
                "allowed_dir": allowed}

    @app.post("/api/run")
    async def run(request: Request):
        check_token(request)
        if app.state.running:
            raise HTTPException(409, "run already in progress")
        body = await request.json()
        script = os.path.realpath(body.get("script", ""))
        if not script.startswith(allowed + os.sep) or not script.endswith(".py"):
            raise HTTPException(400, "script must be a .py file inside allowed dir")
        if not os.path.isfile(script):
            raise HTTPException(400, "script not found")
        from .budget import Budget
        from .events import EventBus
        from .llm import MockClient
        from .pipeline import run_pipeline

        def work():
            app.state.running, app.state.summary, app.state.events = True, None, []
            bus = EventBus(listeners=[listener])
            try:
                app.state.summary = run_pipeline(
                    script, client=MockClient(budget=Budget()), bus=bus,
                    k=int(body.get("k", 2)), verify_k=body.get("verify_k"),
                    timeout=int(body.get("timeout", 180)))
            except Exception as exc:  # surfaced to UI, not hidden
                bus.emit("pipeline_failed", error=str(exc))
                app.state.summary = {"passed": False, "error": str(exc)}
            finally:
                app.state.running = False

        threading.Thread(target=work, daemon=True).start()
        return {"ok": True, "script": script}

    @app.get("/api/events")
    async def events(request: Request):
        check_token(request)

        def gen():
            for ev in list(app.state.events):
                yield f"data: {json.dumps(ev)}\n\n"
            while True:
                try:
                    ev = app.state.bus_queue.get(timeout=15)
                    yield f"data: {json.dumps(ev)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


def serve(host="127.0.0.1", port=8765, allowed_dir=None):
    if host != "127.0.0.1":
        raise SystemExit("serve binds 127.0.0.1 only")
    import uvicorn
    app = create_app(allowed_dir=allowed_dir)
    url = f"http://127.0.0.1:{port}/?token={app.state.token}"
    print(f"MLDoctor dashboard: {url}", flush=True)
    print("Mode: MOCK (no live calls). Keep this terminal open.", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0
