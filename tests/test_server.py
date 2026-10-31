"""Dashboard server: token, allowed-dir, static, mock run (no live)."""
import os
import time

import pytest
from fastapi.testclient import TestClient

from mldoctor.server import create_app

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
H = {"X-MLDoctor-Token": "test-token"}


@pytest.fixture()
def client():
    return TestClient(create_app(allowed_dir=ROOT, token="test-token"))


def test_static_and_mock_badge(client):
    # "/" serves static_next when built, else the vanilla fallback; the
    # vanilla assets stay reachable either way for the fallback dashboard.
    assert "MLDoctor" in client.get("/").text
    assert client.get("/app.js").status_code == 200
    assert client.get("/app.css").status_code == 200


def test_token_required(client):
    assert client.get("/api/state").status_code == 401
    assert client.get("/api/state", headers=H).status_code == 200


def test_allowed_dir_and_ext_enforced(client):
    assert client.post("/api/run", headers=H, json={"script": "/etc/passwd"}).status_code == 400
    outside = client.post("/api/run", headers=H, json={"script": "/tmp/x.py"})
    assert outside.status_code == 400


def test_save_script_roundtrip_and_guards(tmp_path):
    from mldoctor.server import create_app
    app_client = TestClient(create_app(allowed_dir=str(tmp_path), token="test-token"))
    assert app_client.post("/api/scripts", json={"name": "a.py", "content": "x=1"}).status_code == 401
    r = app_client.post("/api/scripts", headers=H, json={"name": "mine.py", "content": "print('hi')"})
    assert r.status_code == 200
    assert r.json()["script"] == os.path.join("uploads", "mine.py")
    assert (tmp_path / "uploads" / "mine.py").read_text() == "print('hi')"
    bad = [{"name": "../evil.py", "content": "x"}, {"name": "a.txt", "content": "x"},
           {"name": "e.py", "content": "   "}, {"name": "big.py", "content": "x" * 200_001},
           {"name": "a/../../b.py", "content": "x"}, {"name": ".hidden.py", "content": "x"},
           {"name": "9lives.py", "content": "x"}, {"name": "sub/dir.py/x.py", "content": "x"}]
    for b in bad:
        assert app_client.post("/api/scripts", headers=H, json=b).status_code == 400
    r = app_client.post("/api/scripts", headers=H, json={"name": "proj/models/mine.py", "content": "x=1"})
    assert r.status_code == 200
    assert r.json()["script"] == os.path.join("uploads", "proj", "models", "mine.py")
    assert (tmp_path / "uploads" / "proj" / "models" / "mine.py").read_text() == "x=1"


@pytest.mark.slow
def test_run_repro_mock_end_to_end(client):
    r = client.post("/api/run", headers=H, json={
        "script": os.path.join(ROOT, "fixtures", "repro.py"), "k": 2, "verify_k": 2})
    assert r.status_code == 200
    for _ in range(60):
        s = client.get("/api/state", headers=H).json()
        if s["summary"] and not s["running"]:
            break
        time.sleep(1)
    assert s["summary"]["passed"] is True
    assert s["summary"]["mock"] is True
    types = [e["type"] for e in s["events"]]
    assert "verification_completed" in types and types[-1] == "pipeline_completed"
