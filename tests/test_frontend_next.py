"""Next frontend serving + demo pacing rules (no live calls)."""
import os

import pytest
from fastapi.testclient import TestClient

import mldoctor.server as srv
from mldoctor.server import create_app, effective_pacing

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
H = {"X-MLDoctor-Token": "test-token"}


def test_demo_pacing_never_in_live():
    assert effective_pacing(True, live=True) is False
    assert effective_pacing(True, live=False) is True
    assert effective_pacing(False, live=False) is False


def test_demo_pacing_state_defaults_off_and_is_mock_only(tmp_path, monkeypatch):
    script = tmp_path / "x.py"
    script.write_text("print('hi')\n")
    app = create_app(allowed_dir=str(tmp_path), token="test-token",
                     live_configured=True)
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get("/api/state", headers=H).json()["demo_pacing"] is False
    # Live request must not enable pacing (403 here: env not actually wired
    # in this app beyond live_configured flag path - pacing stays off on 403
    # only if set before the check; assert the helper-level rule instead).
    r = c.post("/api/run", headers=H, json={"script": str(script),
                                            "live": False, "demo_pacing": True,
                                            "k": 1})
    assert r.status_code == 200
    assert c.get("/api/state", headers=H).json()["demo_pacing"] is True


def test_static_next_preferred_when_present(tmp_path, monkeypatch):
    nxt = tmp_path / "static_next"
    nxt.mkdir()
    (nxt / "index.html").write_text("<title>MLDoctor next</title>NEXT-UI")
    monkeypatch.setattr(srv, "STATIC_NEXT", str(nxt))
    c = TestClient(create_app(allowed_dir=ROOT, token="test-token"))
    assert "NEXT-UI" in c.get("/").text
    assert c.get("/app.js").status_code == 200  # vanilla fallback intact


def test_fixtures_endpoint_lists_allowed_fixtures():
    client = TestClient(create_app(allowed_dir=ROOT, token="test-token"))
    assert client.get("/api/fixtures").status_code == 401
    names = client.get("/api/fixtures", headers=H).json()["fixtures"]
    assert "fixtures/repro.py" in names and "fixtures/diverge.py" in names
    assert all(n.startswith("fixtures/") and n.endswith(".py") for n in names)


def test_dev_cors_allows_both_localhost_origins(monkeypatch):
    monkeypatch.setenv("MLDOCTOR_DEV_CORS", "1")
    client = TestClient(create_app(allowed_dir=ROOT, token="test-token"), raise_server_exceptions=False)
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        r = client.options("/api/run", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                 "Access-Control-Request-Headers": "X-MLDoctor-Token"})
        assert r.headers.get("access-control-allow-origin") == origin, origin
    r = client.options("/api/run", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST",
                                            "Access-Control-Request-Headers": "X-MLDoctor-Token"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_cors_off_by_default(monkeypatch):
    monkeypatch.delenv("MLDOCTOR_DEV_CORS", raising=False)
    client = TestClient(create_app(allowed_dir=ROOT, token="test-token"))
    r = client.options("/api/run", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_vanilla_fallback_when_no_static_next(tmp_path, monkeypatch):
    monkeypatch.setattr(srv, "STATIC_NEXT", str(tmp_path / "missing"))
    c = TestClient(create_app(allowed_dir=ROOT, token="test-token"))
    body = c.get("/").text
    assert "MLDoctor" in body and "mock-badge" in body
