"""Failure handling: clear errors, no stack traces, no hangs."""
import os
import time

import pytest
from fastapi.testclient import TestClient

from mldoctor.runner import classify, run_baseline
from mldoctor.server import create_app

H = {"X-MLDoctor-Token": "t"}


def _app(tmp_path):
    return TestClient(create_app(allowed_dir=str(tmp_path), token="t"))


def test_nonexistent_script_400(tmp_path):
    r = _app(tmp_path).post("/api/run", headers=H, json={"script": str(tmp_path / "nope.py")})
    assert r.status_code == 400 and "not found" in r.text


def test_no_token_401(tmp_path):
    assert _app(tmp_path).post("/api/run", json={"script": "x.py"}).status_code == 401


def test_outside_allowed_dir_400(tmp_path):
    r = _app(tmp_path).post("/api/run", headers=H, json={"script": "/etc/evil.py"})
    assert r.status_code == 400


def test_live_toggle_rejected_when_unconfigured(tmp_path):
    c = _app(tmp_path)
    assert c.get("/api/state", headers=H).json()["live_configured"] is False
    p = tmp_path / "ok.py"
    p.write_text("print('FINAL metric=1.0')\n")
    r = c.post("/api/run", headers=H, json={"script": str(p), "live": True})
    assert r.status_code == 403 and "live not configured" in r.text


def test_crash_script_classified_error(tmp_path):
    p = tmp_path / "crash.py"
    p.write_text("raise RuntimeError('boom')\n")
    runs = run_baseline(str(p), k=1, timeout=30)
    out = classify(runs)
    assert out["symptom"] == "error" and "exited" in out["reason"]


def test_timeout_script_classified_error_not_hang(tmp_path):
    p = tmp_path / "slow.py"
    p.write_text("import time; time.sleep(30)\n")
    runs = run_baseline(str(p), k=1, timeout=2)
    assert runs[0]["returncode"] == 124
    assert classify(runs)["symptom"] == "error"


@pytest.mark.slow
def test_second_run_while_active_409(tmp_path):
    p = tmp_path / "train.py"
    p.write_text(open(os.path.join(os.path.dirname(__file__), "..", "fixtures", "healthy.py")).read())
    c = _app(tmp_path)
    assert c.post("/api/run", headers=H, json={"script": str(p), "k": 3}).status_code == 200
    r = c.post("/api/run", headers=H, json={"script": str(p), "k": 1})
    assert r.status_code == 409
    for _ in range(60):
        s = c.get("/api/state", headers=H).json()
        if s["summary"] and not s["running"]:
            break
        time.sleep(1)
