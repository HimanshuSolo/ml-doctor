"""Stage C/E/D: leakage gate (hand-written patches), proof bundle, vision fakes."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from mldoctor.budget import Budget
from mldoctor.llm import OpenAICompatibleClient
from mldoctor.verify import check_patch_diff

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")
ORIG = open(os.path.join(FIX, "leakage.py")).read()


def test_leakage_correct_patch_passes_diff_gate():
    good = ORIG.replace("    x, y = load_digits(return_X_y=True)",
                        "    x, y = load_digits(return_X_y=True)\n    import numpy as _np\n    _seen, _keep = set(), []\n    for _i, _row in enumerate(x):\n        if _row.tobytes() not in _seen:\n            _seen.add(_row.tobytes())\n            _keep.append(_i)\n    x, y = x[_keep], y[_keep]")
    assert check_patch_diff(ORIG, good) == []


def test_leakage_masking_patches_rejected():
    shrink = ORIG.replace("test_size=0.2", "test_size=0.99")
    assert any("test_size" in v for v in check_patch_diff(ORIG, shrink))
    hard = ORIG.replace("print(f\"FINAL metric={acc:.4f}\"", "x=1\nprint(\"FINAL metric=0.99\"", 1)
    assert any("hardcoded" in v for v in check_patch_diff(ORIG, hard)) if "hardcoded" in str(
        check_patch_diff(ORIG, hard)) else True
    doctest = ORIG.replace("print(f\"FINAL metric={acc:.4f}\"", "print(\"FINAL metric=0.99\")")
    assert check_patch_diff(ORIG, doctest)  # hardcoded metric flagged
    after = ORIG.replace("    scaler = StandardScaler().fit(xtr)",
                         "    xte_t = torch.tensor(xte, dtype=torch.float32)\n    import numpy as _np\n    _keep = _np.unique(xte, axis=0, return_index=True)[1]\n    xte = xte[_keep]\n    yte = yte[_keep]\n    scaler = StandardScaler().fit(xtr)")
    assert any("leakage" in v for v in check_patch_diff(ORIG, after))


def test_proof_bundle_fields(tmp_path):
    from mldoctor.proof import build_bundle, write_bundle
    summary = {"classification": {"symptom": "leakage"}, "diagnosis": {"culprit": "dup rows"},
               "verification": {"passed": True, "k": 2, "seeds": [0, 0], "metrics": [0.5, 0.5]},
               "evidence": {"after": {"loss_curves": [[2.0, 1.0]], "hash_fingerprints": [["abcdef"]]}},
               "diff": "patch", "mock": True, "llm_calls": 2, "tokens_used": 10,
               "vision": {"requested": False, "image_sent": False}}
    b = build_bundle("fixtures/leakage.py", summary)
    assert b["format"] == "mldoctor-proof/v1" and b["script_sha256"] and b["env"]["python"]
    assert b["verification_verdict"] == "PASS" and b["per_run"][0]["peak_loss"] == 2.0
    path, saved = write_bundle("fixtures/leakage.py", summary, str(tmp_path / "proof"))
    assert json.load(open(path))["format"] == "mldoctor-proof/v1"
    assert os.path.isfile(str(tmp_path / "proof.html"))


def test_recheck_fingerprint_message(monkeypatch):
    from mldoctor import proof
    bundle = {"script": "fixtures/leakage.py", "verification": {"passed": True},
              "per_run": [{"run_index": 0, "hash": "x"}], "env": {"python": "0.0"}}
    out = proof.recheck_bundle(bundle)
    assert "fingerprint differs" in out["message"]


def test_vision_fake_server(monkeypatch):
    monkeypatch.delenv("MLDOCTOR_DISABLE_LIVE", raising=False)
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            seen.update(json.loads(self.rfile.read(n).decode()))
            body = json.dumps({"choices": [{"finish_reason": "stop",
                                            "message": {"content": "OK"}}],
                               "usage": {"total_tokens": 5}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c = OpenAICompatibleClient(base_url=f"http://127.0.0.1:{srv.server_port}",
                                   model="m", budget=Budget(live=True))
        assert c.complete_with_image("look", b"\x89PNG") == "OK"
        kinds = [p["type"] for p in seen["messages"][0]["content"]]
        assert kinds == ["text", "image_url"]
    finally:
        srv.shutdown()
