"""Live path vs fake local server only. No real network/model calls."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from mldoctor.budget import Budget, BudgetExceeded, LiveDisabled
from mldoctor.diagnose import ValidationError, parse_diagnosis
from mldoctor.llm import LLMError, OpenAICompatibleClient

MODE = {"kind": "ok"}


class H(BaseHTTPRequestHandler):
    seen = None

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        H.seen = json.loads(self.rfile.read(n).decode())
        H.auth = self.headers.get("Authorization")
        kind = MODE["kind"]
        if kind == "sleep":
            time.sleep(1.5)
        if kind == "http500":
            self.send_response(500); self.end_headers(); self.wfile.write(b"err"); return
        if kind == "reasoning":
            payload = {"model": "fake-reported", "choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps({"symptom": "diverged", "reason": "r", "culprit": "c", "fix_plan": "f"}),
                "reasoning_content": "thinking out loud"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 12, "total_tokens": 22,
                          "completion_tokens_details": {"reasoning_tokens": 7}}}
        elif kind == "nocontent":
            payload = {"model": "m", "choices": [{"finish_reason": "stop", "message": {"reasoning_content": "thinking"}}]}
        elif kind == "empty":
            payload = {"choices": [{"message": {"content": "", "reasoning_content": "all spent thinking"}}],
                       "usage": {"prompt_tokens": 3, "completion_tokens": 50, "total_tokens": 53}}
        elif kind == "badjson":
            payload = {"choices": [{"message": {"content": "not json"}}]}
        elif kind == "missing":
            payload = {"choices": [{"message": {"content": '{"symptom":"diverged"}'}}]}
        elif kind == "shape":
            payload = {"nope": 1}
        else:
            payload = {"choices": [{"message": {"content": json.dumps(
                {"symptom": "diverged", "reason": "r", "culprit": "c", "fix_plan": "f"})}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture()
def srv():
    MODE["kind"] = "ok"
    s = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()


def _client(url, monkeypatch, **kw):
    monkeypatch.delenv("MLDOCTOR_DISABLE_LIVE", raising=False)
    return OpenAICompatibleClient(base_url=url, model="fake",
                                  budget=Budget(live=True), **kw)


def test_valid_and_usage_and_auth(srv, monkeypatch):
    c = _client(srv, monkeypatch, api_key="sekret", max_tokens=42)
    out = parse_diagnosis(c.complete("symptom=diverged", purpose="diagnose"))
    assert out["symptom"] == "diverged"
    assert H.seen["max_tokens"] == 42 and H.auth == "Bearer sekret"
    assert c.budget.calls[0]["usage_total"] == 15
    assert "sekret" not in json.dumps(c.budget.calls)


def test_malformed_and_missing_fields(srv, monkeypatch):
    MODE["kind"] = "badjson"
    with pytest.raises(ValidationError):
        parse_diagnosis(_client(srv, monkeypatch).complete("x", purpose="diagnose"))
    MODE["kind"] = "missing"
    with pytest.raises(ValidationError):
        parse_diagnosis(_client(srv, monkeypatch).complete("x", purpose="diagnose"))
    MODE["kind"] = "shape"
    with pytest.raises(LLMError):
        _client(srv, monkeypatch).complete("x")


def test_http_error_and_timeout(srv, monkeypatch):
    MODE["kind"] = "http500"
    with pytest.raises(LLMError, match="500"):
        _client(srv, monkeypatch).complete("x")
    MODE["kind"] = "sleep"
    with pytest.raises(LLMError):
        _client(srv, monkeypatch, timeout=0.2).complete("x")


def test_cap_and_kill_switch(srv, monkeypatch):
    b = Budget(live=True, max_calls=1)
    monkeypatch.delenv("MLDOCTOR_DISABLE_LIVE", raising=False)
    c = OpenAICompatibleClient(base_url=srv, model="m", budget=b)
    c.complete("x")
    with pytest.raises(BudgetExceeded):
        c.complete("x")
    monkeypatch.setenv("MLDOCTOR_DISABLE_LIVE", "1")
    with pytest.raises(LiveDisabled):
        OpenAICompatibleClient(base_url=srv, model="m",
                               budget=Budget(live=True)).complete("x")


def test_reasoning_content_and_usage_details(srv, monkeypatch):
    # Real Baseten shape: reasoning sits in reasoning_content, the final
    # answer in content, reasoning tokens in completion_tokens_details.
    MODE["kind"] = "reasoning"
    c = _client(srv, monkeypatch, api_key="sekret")
    out = parse_diagnosis(c.complete("symptom=diverged", purpose="diagnose"))
    assert out["symptom"] == "diverged"
    assert c.last_response_info["has_reasoning_content"] is True
    assert c.budget.calls[0]["usage_reasoning"] == 7


def test_missing_content_error_reports_shape(srv, monkeypatch):
    MODE["kind"] = "nocontent"
    with pytest.raises(LLMError, match="has reasoning_content: True"):
        _client(srv, monkeypatch).complete("x")


def test_empty_content_is_clear_error(srv, monkeypatch):
    MODE["kind"] = "empty"
    with pytest.raises(LLMError, match="empty content"):
        _client(srv, monkeypatch).complete("x")


def test_dotenv_loader_and_baseten_fallback(tmp_path, monkeypatch):
    from mldoctor.llm import load_dotenv
    env_file = tmp_path / ".env"
    env_file.write_text("MLDOCTOR_MODEL=from-dotenv\nKEPT=dotenv\n")
    monkeypatch.setenv("KEPT", "real-env")
    monkeypatch.delenv("MLDOCTOR_MODEL", raising=False)
    load_dotenv(str(env_file))
    import os
    assert os.environ["MLDOCTOR_MODEL"] == "from-dotenv"
    assert os.environ["KEPT"] == "real-env"  # existing env wins


def test_missing_api_key_clear_and_not_logged(monkeypatch):
    monkeypatch.delenv("MLDOCTOR_DISABLE_LIVE", raising=False)
    c = OpenAICompatibleClient(base_url="https://example.invalid/v1", model="m",
                               budget=Budget(live=True), api_key=None)
    with pytest.raises(LLMError, match="MLDOCTOR_API_KEY"):
        c.complete("x")
