"""LLM clients: mock offline, live client only against fake local server."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from mldoctor.budget import Budget, BudgetExceeded, LiveDisabled
from mldoctor.llm import MockClient, OpenAICompatibleClient


def test_mock_deterministic_and_capped():
    assert MockClient().complete("hi", purpose="diagnose") == MockClient().complete("hi", purpose="diagnose")
    b = Budget(max_calls=1)
    c = MockClient(budget=b)
    c.complete("hi")
    with pytest.raises(BudgetExceeded):
        c.complete("again")


def test_mock_counts_toward_cap():
    b = Budget(max_calls=2)
    c = MockClient(budget=b, responses={"diagnose": '{"a":1}'})
    assert c.complete("x", purpose="diagnose") == '{"a":1}'
    assert b.call_count == 1
    assert b.calls[0]["live"] is False


class _Handler(BaseHTTPRequestHandler):
    seen = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _Handler.seen = json.loads(self.rfile.read(length).decode())
        body = json.dumps({"choices": [{"message": {"content": "fake-reply"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv


def test_live_client_against_fake_server(monkeypatch):
    monkeypatch.delenv("MLDOCTOR_DISABLE_LIVE", raising=False)
    srv = _server()
    try:
        b = Budget(live=True)
        c = OpenAICompatibleClient(base_url=f"http://127.0.0.1:{srv.server_port}",
                                   model="fake", budget=b)
        assert c.complete("hello", purpose="chat") == "fake-reply"
        assert _Handler.seen["model"] == "fake"
        assert _Handler.seen["messages"][0]["content"] == "hello"
        assert b.calls[0]["live"] is True
    finally:
        srv.shutdown()


def test_live_client_blocked_without_live_flag():
    b = Budget(live=False)
    c = OpenAICompatibleClient(base_url="http://127.0.0.1:1", model="m", budget=b)
    with pytest.raises(LiveDisabled):
        c.complete("hi")


def test_live_client_blocked_by_kill_switch(monkeypatch):
    monkeypatch.setenv("MLDOCTOR_DISABLE_LIVE", "1")
    b = Budget(live=True)
    c = OpenAICompatibleClient(base_url="http://127.0.0.1:1", model="m", budget=b)
    with pytest.raises(LiveDisabled):
        c.complete("hi")


def test_image_not_implemented_pending_docs():
    b = Budget(live=True)
    c = OpenAICompatibleClient(base_url="http://127.0.0.1:1", model="m", budget=b)
    with pytest.raises(NotImplementedError):
        c.complete_with_image("prompt", image=b"bytes")
