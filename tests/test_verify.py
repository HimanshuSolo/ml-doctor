"""Verify gate: run counts, anti-masking diffs, hand-written patches (no model)."""
import os

import pytest
import tempfile

from mldoctor.patch import apply_patch
from mldoctor.verify import check_patch_diff, required_runs, verify_fix

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")

REPRO_FIX = {"path": "repro.py", "edits": [
    {"old": "    np.random.seed(SEED)",
     "new": "    random.seed(SEED)\n    np.random.seed(SEED)"}], "rationale": "seed stdlib random"}

DIVERGE_FIX = {"path": "diverge.py", "edits": [
    {"old": "from sklearn.model_selection import train_test_split",
     "new": "from sklearn.model_selection import train_test_split\nfrom sklearn.preprocessing import StandardScaler"},
    {"old": "LR = 5.0", "new": "LR = 0.05"},
    {"old": "    # BUG: raw pixel values 0-16, no normalization.\n    xtr_t = torch.tensor(xtr, dtype=torch.float32)",
     "new": "    scaler = StandardScaler().fit(xtr)\n    xtr_t = torch.tensor(scaler.transform(xtr), dtype=torch.float32)"},
    {"old": "    xte_t = torch.tensor(xte, dtype=torch.float32)",
     "new": "    xte_t = torch.tensor(scaler.transform(xte), dtype=torch.float32)"}],
    "rationale": "sane lr plus input normalization"}


def _src(name):
    with open(os.path.join(FIX, name)) as fh:
        return fh.read()


def _write_tmp(text):
    fh = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    fh.write(text)
    fh.close()
    return fh.name


def test_required_runs_statistics_aware():
    assert required_runs("non_reproducible") == 10
    assert required_runs("diverged") == 5
    assert required_runs("healthy") == 2
    assert required_runs("non_reproducible") > required_runs("diverged")


def test_correct_patches_have_clean_diffs():
    assert check_patch_diff(_src("repro.py"), apply_patch(_src("repro.py"), REPRO_FIX)) == []
    assert check_patch_diff(_src("diverge.py"), apply_patch(_src("diverge.py"), DIVERGE_FIX)) == []


def test_repro_masking_attempts_flagged():
    orig = _src("repro.py")
    no_shuffle = orig.replace("        random.shuffle(idx)", "        pass  # no shuffle")
    hard_metric = orig.replace('print(f"FINAL metric={acc:.4f}"', 'print("FINAL metric=0.9000"')
    zero_epochs = orig.replace("EPOCHS = 3", "EPOCHS = 0")
    assert check_patch_diff(orig, no_shuffle) == ["removes shuffle instead of seeding"]
    assert check_patch_diff(orig, hard_metric) == ["hardcoded metric"]
    assert check_patch_diff(orig, zero_epochs) == ["disables training (EPOCHS=0)"]


def test_diverge_masking_attempts_flagged():
    orig = _src("diverge.py")
    clip = orig.replace("            loss.backward()",
                        "            loss = torch.nan_to_num(loss)\n            loss.backward()")
    hard_metric = orig.replace('print(f"FINAL metric={acc:.4f}"', 'print("FINAL metric=0.9000"')
    zero_epochs = orig.replace("EPOCHS = 3", "EPOCHS = 0")
    assert check_patch_diff(orig, clip) == ["masks loss (nan_to_num)"]
    assert check_patch_diff(orig, hard_metric) == ["hardcoded metric"]
    assert check_patch_diff(orig, zero_epochs) == ["disables training (EPOCHS=0)"]


def test_verify_rejects_masking_without_runs(tmp_path):
    orig = _src("repro.py")
    masked = orig.replace("EPOCHS = 3", "EPOCHS = 0")
    p = tmp_path / "masked.py"
    p.write_text(masked)
    out = verify_fix(str(p), "non_reproducible", original_text=orig)
    assert out["passed"] is False
    assert out["k"] == 0
    assert out["violations"]


@pytest.mark.slow
def test_verify_repro_fix_passes():
    path = _write_tmp(apply_patch(_src("repro.py"), REPRO_FIX))
    try:
        out = verify_fix(path, "non_reproducible", k=2, original_text=_src("repro.py"))
        assert out["passed"] is True
        assert out["symptom"] == "healthy"
    finally:
        os.unlink(path)


@pytest.mark.slow
def test_verify_diverge_fix_passes():
    path = _write_tmp(apply_patch(_src("diverge.py"), DIVERGE_FIX))
    try:
        out = verify_fix(path, "diverged", k=2, original_text=_src("diverge.py"))
        assert out["passed"] is True
        assert out["symptom"] == "healthy"
        assert out["seeds"] == [0, 1] and out["mode"] == "seeds"
    finally:
        os.unlink(path)
