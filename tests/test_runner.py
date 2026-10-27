"""Symptom classification: unit rules + fixture integration (offline)."""
import math
import os

from mldoctor.runner import classify, run_baseline

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _run(hashes, losses, metric=0.9, code=0):
    return {"returncode": code, "stdout": "", "stderr": "",
            "telemetry": [{"step": i, "loss": l, "grad_norm": 0.1,
                           "param_hash": h}
                          for i, (l, h) in enumerate(zip(losses, hashes))],
            "final_metric": metric}


def test_healthy_when_hashes_identical():
    runs = [_run(["a", "b", "c"], [2.0, 1.5, 1.0]) for _ in range(3)]
    assert classify(runs)["symptom"] == "healthy"


def test_non_reproducible_reports_first_step():
    runs = [_run(["a", "b", "c"], [2.0, 1.5, 1.0]),
            _run(["a", "X", "c"], [2.0, 1.4, 1.0])]
    out = classify(runs)
    assert out["symptom"] == "non_reproducible"
    assert out["first_step"] == 1


def test_diverged_on_nonfinite_loss():
    runs = [_run(["a", "b"], [2.0, math.inf])]
    assert classify(runs)["symptom"] == "diverged"


def test_diverged_on_loss_ratio():
    runs = [_run(["a", "b"], [1.0, 25.0])]
    assert classify(runs)["symptom"] == "diverged"


def test_error_on_crash():
    runs = [_run(["a"], [1.0], code=1)]
    assert classify(runs)["symptom"] == "error"


def test_healthy_fixture_classified_healthy():
    runs = run_baseline(os.path.join(FIX, "healthy.py"), k=3, seed=0)
    assert classify(runs)["symptom"] == "healthy"


def test_repro_fixture_classified_non_reproducible():
    runs = run_baseline(os.path.join(FIX, "repro.py"), k=3, seed=0)
    assert classify(runs)["symptom"] == "non_reproducible"


def test_diverge_fixture_classified_diverged():
    runs = run_baseline(os.path.join(FIX, "diverge.py"), k=3, seed=0)
    assert classify(runs)["symptom"] == "diverged"
