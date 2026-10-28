"""Per-run data the Next UI needs: verify_progress payload + evidence shape."""
import json

import mldoctor.verify as verify


def _run(hashes, losses, rc=0):
    return {"returncode": rc, "final_metric": 1.0,
            "telemetry": [{"loss": l, "param_hash": h}
                          for h, l in zip(hashes, losses)]}


def _script(tmp_path):
    p = tmp_path / "patched.py"
    p.write_text("x = 2\n")
    return str(p)


def test_progress_payload_same_seed_identical_then_different(tmp_path, monkeypatch):
    runs = [_run(["aaaaaa111111", "bbbbbb222222"], [2.0, 1.0]),
            _run(["aaaaaa111111", "cccccc333333"], [2.0, 1.5])]
    monkeypatch.setattr(verify, "run_baseline", lambda *a, **k: [runs.pop(0)])
    seen = []
    verify.verify_fix(_script(tmp_path), "non_reproducible", k=2,
                      original_text="x = 1\n", progress=seen.append)
    assert [e["run_index"] for e in seen] == [0, 1]
    assert seen[0]["status"] == "identical" and seen[1]["status"] == "different"
    for e in seen:
        assert set(e) >= {"n_done", "n_total", "n_failed", "run_index",
                          "param_hash", "final_loss", "peak_loss", "status"}
        assert len(e["param_hash"]) == 6
        json.dumps(e, allow_nan=False)
    assert seen[0]["final_loss"] == 1.0 and seen[0]["peak_loss"] == 2.0


def test_progress_payload_diverged_and_finite(tmp_path, monkeypatch):
    runs = [_run(["aaaaaa111111"], [1.0]), _run(["bbbbbb222222", "cccccc333333"], [1.0, 50.0])]
    monkeypatch.setattr(verify, "run_baseline", lambda *a, **k: [runs.pop(0)])
    seen = []
    verify.verify_fix(_script(tmp_path), "diverged", k=2,
                      original_text="x = 1\n", progress=seen.append)
    assert [e["status"] for e in seen] == ["finite", "diverged"]
    json.dumps(seen, allow_nan=False)


def test_progress_payload_nonfinite_is_json_safe(tmp_path, monkeypatch):
    runs = [_run(["aaaaaa111111"], [float("nan")])]
    monkeypatch.setattr(verify, "run_baseline", lambda *a, **k: [runs.pop(0)])
    seen = []
    verify.verify_fix(_script(tmp_path), "non_reproducible", k=1,
                      original_text="x = 1\n", progress=seen.append)
    assert seen[0]["status"] == "diverged"
    assert seen[0]["final_loss"] is None
    json.dumps(seen, allow_nan=False)


def test_default_verify_counts_are_spec(tmp_path, monkeypatch):
    # Dashboard launcher sends verify_k=null, so verify_fix must default to
    # 10 same-seed runs for non_reproducible and 5 seeds for diverged.
    assert verify.required_runs("non_reproducible") == 10
    assert verify.required_runs("diverged") == 5
    calls = []
    def fake(*a, **k):
        calls.append(k.get("seed", a[2] if len(a) > 2 else None))
        return [_run(["aaaaaa111111"], [1.0])]
    monkeypatch.setattr(verify, "run_baseline", fake)
    seen = []
    verify.verify_fix(_script(tmp_path), "non_reproducible",
                      original_text="x = 1\n", progress=seen.append)
    assert len(calls) == 10 and seen[-1]["n_total"] == 10
    calls.clear(); seen.clear()
    verify.verify_fix(_script(tmp_path), "diverged",
                      original_text="x = 1\n", progress=seen.append)
    assert len(calls) == 5 and seen[-1]["n_total"] == 5


def test_evidence_loss_series_downsampled_to_200():
    run = _run(["a" * 16] * 500, list(range(500)))
    ev = verify.evidence_of([run])
    assert 0 < len(ev["loss_curves"][0]) <= 200
    assert ev["loss_curves"][0][-1] == 499  # last measured point kept
    assert len(ev["hash_fingerprints"][0]) == 500  # per-step hashes kept
    json.dumps(ev, allow_nan=False)
