"""Verify gate: diff anti-masking checks + statistics-aware reruns.

Diff checks run first (no subprocess); reruns only on clean diffs.
Spec counts: non_reproducible = 10 same-seed runs (hash identity);
diverged = 5 seeds (one run each, every seed must stay finite/sane).
"""
import math
import re

from .runner import classify, run_baseline

REQUIRED_RUNS = {"healthy": 2, "diverged": 5, "non_reproducible": 10, "error": 2}
_LOSS_MASKS = ("nan_to_num", "torch.clamp", "clip_grad", "loss = min", "loss = max")


def required_runs(symptom, minimum=2):
    return max(minimum, REQUIRED_RUNS.get(symptom, 3))


def check_patch_diff(original, patched):
    v = []
    if patched == original:
        return ["empty patch"]
    if re.search(r"FINAL metric=\d", patched):
        v.append("hardcoded metric")
    mo = re.search(r"EPOCHS\s*=\s*(\d+)", original)
    mp = re.search(r"EPOCHS\s*=\s*(\d+)", patched)
    if mp and (not mo or mp.group(1) != mo.group(1)):
        v.append("disables training (EPOCHS=0)" if mp.group(1) == "0"
                 else f"changes training (EPOCHS {mo.group(1) if mo else '?'} -> {mp.group(1)})")
    if "except" in patched and "except" not in original:
        v.append("swallows errors (adds except)")
    elif re.search(r"^\s*try\s*:", patched, re.M) and not re.search(r"^\s*try\s*:", original, re.M):
        v.append("swallows errors (adds try)")
    for tok in _LOSS_MASKS:
        if tok in patched and tok not in original:
            v.append(f"masks loss ({tok})")
    if "random.shuffle" in original and "random.shuffle" not in patched:
        v.append("removes shuffle instead of seeding")
    if re.search(r"\.seed\(\d+\)", patched) and not re.search(r"\.seed\(\d+\)", original):
        v.append("fixed seed literal ignores MLDOCTOR_SEED")
    # Dataset / model / check integrity from changed lines.
    import difflib
    sm = difflib.SequenceMatcher(None, original.splitlines(), patched.splitlines())
    removed, added = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"): removed += original.splitlines()[i1:i2]
        if tag in ("insert", "replace"): added += patched.splitlines()[j1:j2]
    def _val(text, pat):
        m = re.search(pat, text); return m.group(1) if m else None
    if _val(original, r"test_size=([\d.]+)") != _val(patched, r"test_size=([\d.]+)"):
        v.append("changes dataset (test_size)")
    if _val(original, r"load_digits\(([^)]*)\)") != _val(patched, r"load_digits\(([^)]*)\)"):
        v.append("changes dataset (load_digits)")
    if any(tok in "\n".join(added) for tok in ("Subset(", "random_split", "[:500]", "[:100]")):
        v.append("changes dataset (subset)")
    if any("nn.Linear" in l or "nn.Sequential" in l for l in removed + added):
        v.append("changes model architecture")
    for l in removed:
        if ("assert" in l or "isfinite" in l) and l.strip() not in patched:
            v.append("removes or weakens a check"); break
    # Dedupe, preserve order.
    return list(dict.fromkeys(v))


MAX_SERIES_POINTS = 200


def _finite_or_none(v):
    return v if (v is not None and math.isfinite(v)) else None


def downsample(series, max_points=MAX_SERIES_POINTS):
    """Evenly spaced measured points, always keeping the last; ~max_points max."""
    if len(series) <= max_points:
        return list(series)
    idx = [round(i * (len(series) - 1) / (max_points - 1))
           for i in range(max_points)]
    return [series[i] for i in dict.fromkeys(idx)]


def run_payload(run, run_index, status):
    """Per-run fields the UI renders, from harness telemetry only."""
    tel = run.get("telemetry") or []
    losses = [t["loss"] for t in tel if t.get("loss") is not None]
    finite = [x for x in losses if math.isfinite(x)]
    return {
        "run_index": run_index,
        "param_hash": (tel[-1]["param_hash"][:6] if tel else None),
        "final_loss": _finite_or_none(losses[-1] if losses else None),
        "peak_loss": _finite_or_none(max(finite) if finite else None),
        "status": status,
    }


def evidence_of(runs):
    return {
        "loss_curves": [downsample([_finite_or_none(t["loss"])
                                     for t in r["telemetry"]
                                     if t["loss"] is not None])
                        for r in runs],
        "hash_fingerprints": [[t["param_hash"][:6] for t in r["telemetry"]]
                              for r in runs],
        "metrics": [r["final_metric"] for r in runs],
    }


def verify_fix(patched_script, original_symptom, expected="healthy",
               k=None, seed=0, timeout=180, original_text=None, progress=None):
    with open(patched_script) as fh:
        patched_text = fh.read()
    violations = check_patch_diff(original_text, patched_text) if original_text else []
    if violations:
        return {"passed": False, "symptom": None, "reason": "masking: " + "; ".join(violations),
                "violations": violations, "k": 0, "metrics": [], "seeds": [], "mode": "diff"}
    k = k or required_runs(original_symptom)
    def emit(done, failed, run=None, status="finite"):
        if progress:
            payload = {"n_done": done, "n_total": k, "n_failed": failed}
            if run is not None:
                payload.update(run_payload(run, done - 1, status))
            progress(payload)

    if original_symptom == "diverged":
        seeds = list(range(seed, seed + k))
        runs, bad, n_failed = [], None, 0
        for i, s in enumerate(seeds):
            run = run_baseline(patched_script, k=1, seed=s, timeout=timeout)[0]
            runs.append(run)
            losses = [t["loss"] for t in run["telemetry"] if t["loss"] is not None]
            cur = None
            if run["returncode"] != 0:
                cur = ("error", f"seed {s} exited {run['returncode']}")
            elif any(not math.isfinite(x) for x in losses):
                cur = ("diverged", f"non-finite loss at seed {s}")
            elif losses and max(losses) > max(1.0, losses[0]) * 10.0:
                cur = ("diverged", f"peak loss {max(losses):.3g} > 10x initial at seed {s}")
            if cur:
                n_failed += 1
                bad = bad or cur
            emit(i + 1, n_failed, run,
                 "error" if (cur and cur[0] == "error") else
                 "diverged" if cur else "finite")
        ok = bad is None and expected == "healthy"
        return {"passed": ok, "symptom": "healthy" if bad is None else bad[0],
                "reason": "finite, sane losses on all seeds" if bad is None else bad[1],
                "violations": [], "k": k, "seeds": seeds, "mode": "seeds",
                "metrics": [r["final_metric"] for r in runs], "evidence": evidence_of(runs)}
    runs, ref, n_failed = [], None, 0
    for i in range(k):
        run = run_baseline(patched_script, k=1, seed=seed, timeout=timeout)[0]
        runs.append(run)
        seq = tuple(t["param_hash"] for t in run["telemetry"])
        losses = [t["loss"] for t in run["telemetry"] if t["loss"] is not None]
        bad_run = (run["returncode"] != 0 or any(not math.isfinite(x) for x in losses)
                   or (ref is not None and seq != ref))
        if ref is None:
            ref = seq
        if bad_run:
            n_failed += 1
        status = ("diverged" if any(not math.isfinite(x) for x in losses)
                  else "error" if run["returncode"] != 0
                  else "different" if (ref is not None and seq != ref)
                  else "identical")
        emit(i + 1, n_failed, run, status)
    result = classify(runs)
    ok = result["symptom"] == expected
    return {"passed": ok, "symptom": result["symptom"], "reason": result["reason"],
            "violations": [], "k": k, "metrics": result["metrics"],
            "seeds": [seed] * k, "mode": "same-seed", "evidence": evidence_of(runs)}
