"""Mock keyed by symptom: diverge gets a fitting fix; shuffle fix rejected."""
import os

import pytest

from mldoctor.budget import Budget
from mldoctor.llm import MockClient
from mldoctor.patch import apply_patch, diagnose_and_patch, parse_patch
from mldoctor.pipeline import run_pipeline
from mldoctor.verify import check_patch_diff, verify_fix

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _src(name):
    return open(os.path.join(FIX, name)).read()


def test_mock_keyed_by_symptom_diverge():
    src = _src("diverge.py")
    client = MockClient(budget=Budget(max_calls=4))
    d, p, patched = diagnose_and_patch(
        {"symptom": "diverged", "reason": "peak loss"}, src, client)
    assert d["symptom"] == "diverged"
    assert "LR = 0.05" in patched and "StandardScaler" in patched
    assert "random.seed(SEED)\n    np.random.seed(SEED)" not in patched or "LR = 0.05" in patched
    assert check_patch_diff(src, patched) == []


@pytest.mark.slow
def test_mock_diverge_pipeline_passes_and_writes_mldoctor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = run_pipeline(os.path.join(FIX, "diverge.py"), k=2, verify_k=2)
    assert s["passed"] is True and s["diagnosis"]["symptom"] == "diverged"
    assert os.path.dirname(s["patched_path"]) == str(tmp_path / ".mldoctor" / "patched")


@pytest.mark.slow
def test_shuffle_patch_rejected_for_diverge(tmp_path):
    src = _src("diverge.py")
    # The non_reproducible mock patch (seed stdlib random), applied verbatim.
    client = MockClient(budget=Budget(max_calls=2))
    text = client.complete("symptom=non_reproducible", purpose="patch")
    patched = apply_patch(src, parse_patch(text))
    p = tmp_path / "diverge_shufflefix.py"
    p.write_text(patched)
    out = verify_fix(str(p), "diverged", k=2, original_text=src)
    assert out["passed"] is False
    assert out["symptom"] == "diverged"
