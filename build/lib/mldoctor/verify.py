"""Verify gate: diff anti-masking checks + statistics-aware reruns.

Diff checks run first (no subprocess); reruns only on clean diffs.
required_runs: non_reproducible needs most runs (flake escape prob
2*0.5^k; k=5 -> ~6% false-healthy). Deterministic symptoms need fewer.
"""
import re

from .runner import classify, run_baseline

REQUIRED_RUNS = {"healthy": 2, "diverged": 3, "non_reproducible": 5, "error": 2}
_LOSS_MASKS = ("nan_to_num", "torch.clamp", "clip_grad", "loss = min", "loss = max")


def required_runs(symptom, minimum=2):
    return max(minimum, REQUIRED_RUNS.get(symptom, 3))


def check_patch_diff(original, patched):
    v = []
    if patched == original:
        return ["empty patch"]
    if re.search(r"FINAL metric=\d", patched):
        v.append("hardcoded metric")
    if re.search(r"EPOCHS\s*=\s*0", patched):
        v.append("disables training (EPOCHS=0)")
    if "except" in patched and "except" not in original:
        v.append("swallows errors (adds except)")
    for tok in _LOSS_MASKS:
        if tok in patched and tok not in original:
            v.append(f"masks loss ({tok})")
    if "random.shuffle" in original and "random.shuffle" not in patched:
        v.append("removes shuffle instead of seeding")
    if re.search(r"\.seed\(\d+\)", patched) and not re.search(r"\.seed\(\d+\)", original):
        v.append("fixed seed literal ignores MLDOCTOR_SEED")
    return v


def verify_fix(patched_script, original_symptom, expected="healthy",
               k=None, seed=0, timeout=180, original_text=None):
    with open(patched_script) as fh:
        patched_text = fh.read()
    violations = check_patch_diff(original_text, patched_text) if original_text else []
    if violations:
        return {"passed": False, "symptom": None, "reason": "masking: " + "; ".join(violations),
                "violations": violations, "k": 0, "metrics": []}
    k = k or required_runs(original_symptom)
    runs = run_baseline(patched_script, k=k, seed=seed, timeout=timeout)
    result = classify(runs)
    ok = result["symptom"] == expected
    return {"passed": ok, "symptom": result["symptom"], "reason": result["reason"],
            "violations": [], "k": k, "metrics": result["metrics"]}
