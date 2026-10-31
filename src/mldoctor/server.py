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
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
STATIC_NEXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static_next")
DEMO_PACING_DELAY = 0.35


def effective_pacing(demo_pacing, live):
    """Demo pacing is MOCK-only; never active for a live run."""
    return bool(demo_pacing) and not bool(live)


def create_app(allowed_dir=None, token=None, live_configured=None, call_cap=8,
               dev_cors=False):
    allowed = os.path.realpath(allowed_dir or os.getcwd())
    app = FastAPI(title="MLDoctor")
    app.state.token = token or secrets.token_urlsafe(18)
    app.state.allowed_dir = allowed
    app.state.bus_queue = queue.Queue()
    app.state.summary = None
    app.state.running = False
    app.state.events = []
    if live_configured is None:
        live_configured = bool(os.environ.get("MLDOCTOR_BASE_URL")
                               and os.environ.get("MLDOCTOR_MODEL")
                               and os.environ.get("MLDOCTOR_API_KEY"))
    app.state.live_configured = live_configured
    app.state.call_cap = int(os.environ.get("MLDOCTOR_MAX_CALLS", call_cap))
    app.state.demo_pacing = False
    if dev_cors or os.environ.get("MLDOCTOR_DEV_CORS") == "1":
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:3000",
                                                             "http://localhost:3000"],
                           allow_methods=["GET", "POST"], allow_headers=["*"])

    def check_token(request):
        tok = request.headers.get("x-mldoctor-token") or request.query_params.get("token")
        if tok != app.state.token:
            raise HTTPException(401, "bad or missing token")

    def listener(ev):
        if app.state.demo_pacing:
            time.sleep(DEMO_PACING_DELAY)
        app.state.events.append(ev)
        app.state.bus_queue.put(ev)

    def _next_index():
        p = os.path.join(STATIC_NEXT, "index.html")
        return p if os.path.isfile(p) else None

    @app.get("/")
    def index():
        nxt = _next_index()
        return FileResponse(nxt or os.path.join(STATIC, "index.html"))

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
                "live_configured": app.state.live_configured,
                "call_cap": app.state.call_cap,
                "demo_pacing": app.state.demo_pacing,
                "allowed_dir": allowed}

    @app.get("/api/fixtures")
    def fixtures(request: Request):
        check_token(request)
        fixdir = os.path.join(allowed, "fixtures")
        out = []
        if os.path.isdir(fixdir):
            for name in sorted(os.listdir(fixdir)):
                if name.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(fixdir, name), allowed))
        return {"fixtures": out}

    @app.post("/api/scripts")
    async def save_script(request: Request):
        """Save pasted user code as a runnable .py file inside allowed dir.

        Lets an end user feed their own ML script to the pipeline without
        touching the repo. Guarded like /api/run: token, basename only, .py
        extension, size cap; always lands in allowed/uploads/."""
        check_token(request)
        body = await request.json()
        name = str(body.get("name", ""))
        content = body.get("content", "")
        parts = [seg for seg in name.replace("\\", "/").split("/") if seg not in ("", ".")]
        def _ok_seg(seg, allow_ext):
            core = seg[:-3] if allow_ext and seg.endswith(".py") else seg
            if allow_ext != seg.endswith(".py"):
                return False
            return bool(core) and core[0].isalpha() and all(
                c.isalnum() or c in "_- " for c in core)
        if (not parts or ".." in parts
                or not _ok_seg(parts[-1], True)
                or not all(_ok_seg(seg, False) and "." not in seg for seg in parts[:-1])):
            raise HTTPException(400, "name must be a .py path of plain filename segments")
        if not isinstance(content, str) or not content.strip():
            raise HTTPException(400, "content must be non-empty text")
        if len(content) > 200_000:
            raise HTTPException(400, "content too large (max 200k characters)")
        updir = os.path.join(allowed, "uploads")
        dest = os.path.realpath(os.path.join(updir, *parts))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not dest.startswith(updir + os.sep):
            raise HTTPException(400, "invalid filename")
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "script": os.path.relpath(dest, allowed)}

    @app.get("/api/report")
    def report(request: Request):
        check_token(request)
        if not app.state.summary:
            raise HTTPException(404, "no finished run yet")
        from .report import render_report
        from fastapi.responses import Response
        return Response(render_report(app.state.summary),
                        media_type="text/html",
                        headers={"Content-Disposition": "attachment; filename=mldoctor-report.html"})

    @app.get("/api/proof.json")
    def proof_json(request: Request):
        check_token(request)
        if not app.state.summary:
            raise HTTPException(404, "no finished run yet")
        from . import proof as proof_mod
        from fastapi.responses import JSONResponse
        bundle = proof_mod.build_bundle(app.state.summary.get("script", "?"),
                                        app.state.summary)
        return JSONResponse(bundle, headers={
            "Content-Disposition": "attachment; filename=mldoctor-proof.json"})

    @app.get("/api/proof.html")
    def proof_html(request: Request):
        check_token(request)
        if not app.state.summary:
            raise HTTPException(404, "no finished run yet")
        from . import proof as proof_mod
        from fastapi.responses import Response
        bundle = proof_mod.build_bundle(app.state.summary.get("script", "?"),
                                        app.state.summary)
        return Response(proof_mod.bundle_html(bundle), media_type="text/html",
                        headers={"Content-Disposition": "attachment; filename=mldoctor-proof.html"})

    @app.post("/api/run")
    async def run(request: Request):
        check_token(request)
        if app.state.running:
            raise HTTPException(409, "run already in progress")
        body = await request.json()
        want_live = bool(body.get("live"))
        if want_live and not app.state.live_configured:
            raise HTTPException(403, "live not configured on server "
                                     "(set MLDOCTOR_BASE_URL, MLDOCTOR_MODEL, MLDOCTOR_API_KEY)")
        script = os.path.realpath(body.get("script", ""))
        if not script.startswith(allowed + os.sep) or not script.endswith(".py"):
            raise HTTPException(400, "script must be a .py file inside allowed dir")
        if not os.path.isfile(script):
            raise HTTPException(400, "script not found")
        from .budget import Budget
        from .events import EventBus
        from .llm import MockClient, OpenAICompatibleClient
        from .pipeline import run_pipeline

        def make_client():
            if not want_live:
                return MockClient(budget=Budget(max_calls=app.state.call_cap))
            return OpenAICompatibleClient.from_env(
                Budget(max_calls=app.state.call_cap, live=True))

        def work():
            app.state.running, app.state.summary, app.state.events = True, None, []
            bus = EventBus(listeners=[listener])
            try:
                app.state.summary = run_pipeline(
                    script, client=make_client(), bus=bus,
                    k=int(body.get("k", 2)), verify_k=body.get("verify_k"),
                    timeout=int(body.get("timeout", 180)),
                    investigate=bool(body.get("investigate")),
                    vision=bool(body.get("vision")))
            except Exception as exc:  # surfaced to UI, not hidden
                bus.emit("pipeline_failed", error=str(exc))
                app.state.summary = {"passed": False, "error": str(exc)}
            finally:
                app.state.running = False

        app.state.demo_pacing = effective_pacing(body.get("demo_pacing"), want_live)
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

    if os.path.isfile(os.path.join(STATIC_NEXT, "index.html")):
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=STATIC_NEXT, html=True),
                  name="static_next")
    return app


def serve(host="127.0.0.1", port=8765, allowed_dir=None):
    # Non-local bind is an explicit opt-in (used by the Docker image, where the
    # container network is the boundary). The per-launch token still gates /api/*.
    if host != "127.0.0.1" and os.environ.get("MLDOCTOR_ALLOW_NONLOCAL") != "1":
        raise SystemExit("serve binds 127.0.0.1 only "
                         "(set MLDOCTOR_ALLOW_NONLOCAL=1 to override, e.g. in Docker)")
    import uvicorn
    app = create_app(allowed_dir=allowed_dir)
    url = f"http://127.0.0.1:{port}/?token={app.state.token}"
    print(f"MLDoctor dashboard: {url}", flush=True)
    print("Mode: MOCK (no live calls). Keep this terminal open.", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0
