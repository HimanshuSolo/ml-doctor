"""Part 2 gate tests: hand-written patches, no model. Fast = diff-only."""
import os

import pytest

from mldoctor.patch import PatchError, apply_patch
from mldoctor.verify import check_patch_diff, verify_fix

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _src(name):
    return open(os.path.join(FIX, name)).read()


def _both():
    return [("repro.py", _src("repro.py")), ("diverge.py", _src("diverge.py"))]


def test_gate_rejects_epochs_change():
    for _, s in _both():
        assert check_patch_diff(s, s.replace("EPOCHS = 3", "EPOCHS = 1"))


def test_gate_rejects_dataset_change():
    for _, s in _both():
        assert check_patch_diff(s, s.replace("test_size=0.2", "test_size=0.5"))


def test_gate_rejects_model_change():
    for _, s in _both():
        assert check_patch_diff(s, s.replace("nn.Linear(64, 32)", "nn.Linear(64, 8)"))


def test_gate_rejects_try_except_and_nan_clamp():
    for _, s in _both():
        wrapped = s.replace("            loss.backward()",
                            "            try:\n                loss = torch.nan_to_num(loss)\n                loss.backward()\n            except Exception:\n                pass")
        v = check_patch_diff(s, wrapped)
        assert any("except" in x or "nan_to_num" in x for x in v)


def test_gate_rejects_fake_metric_and_empty():
    for _, s in _both():
        hard = s.replace('print(f"FINAL metric={acc:.4f}"', 'print("FINAL metric=0.9000"')
        assert "hardcoded metric" in check_patch_diff(s, hard)
        assert check_patch_diff(s, s) == ["empty patch"]


def test_gate_rejects_removed_check():
    s = _src("diverge.py")
    weakened = s.replace("        if torch.isfinite(logits).all():\n", "        if True:\n")
    assert "removes or weakens a check" in check_patch_diff(s, weakened)


def test_patch_not_applying_is_clear_error():
    with pytest.raises(PatchError):
        apply_patch(_src("repro.py"),
                    {"path": "x", "edits": [{"old": "NOPE_NOT_PRESENT", "new": "y"}],
                     "rationale": "r"})


@pytest.mark.slow
def test_gate_broken_patch_fails_without_crash(tmp_path):
    orig = _src("repro.py")
    p = tmp_path / "broken.py"
    p.write_text(orig + "\nthis is not python !!!\n")
    out = verify_fix(str(p), "non_reproducible", k=2, original_text=orig)
    assert out["passed"] is False and out["symptom"] == "error"
