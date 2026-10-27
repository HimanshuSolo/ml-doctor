"""Run K baselines through the harness and classify the symptom.

Rules: diverged (non-finite loss, or final loss above a ratio of the initial
one), non_reproducible (parameter-hash sequences differ across same-seed
runs), healthy. Crashed runs report as error (outside the MVP classes).
"""
import math
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from .harness import THREADS_ENV, run_script

DIVERGE_RATIO = 10.0


def run_baseline(script, k=5, seed=0, timeout=120, jobs=1, threads=None):
    """Run script k times with the same seed. jobs>1 uses a thread pool
    (subprocess-based; no multiprocessing). Returns list of run dicts."""
    tmpdir = tempfile.mkdtemp(prefix="mldoctor_")

    def one(i):
        extra = {THREADS_ENV: str(threads)} if threads else None
        return run_script(script, os.path.join(tmpdir, f"run{i}.jsonl"),
                          seed=seed, timeout=timeout, extra_env=extra)

    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            return list(pool.map(one, range(k)))
    return [one(i) for i in range(k)]


def _losses(run):
    return [t["loss"] for t in run["telemetry"] if t["loss"] is not None]


def classify(runs, diverge_ratio=DIVERGE_RATIO):
    """Classify symptom from baseline runs. Returns a small details dict."""
    crashed = [i for i, r in enumerate(runs) if r["returncode"] != 0]
    if crashed:
        i = crashed[0]
        return {"symptom": "error",
                "reason": f"run {i} exited {runs[i]['returncode']}",
                "first_step": None,
                "metrics": [r["final_metric"] for r in runs]}
    for i, run in enumerate(runs):
        losses = _losses(run)
        if any(not math.isfinite(x) for x in losses):
            return {"symptom": "diverged",
                    "reason": f"non-finite loss in run {i}",
                    "first_step": None,
                    "metrics": [r["final_metric"] for r in runs]}
        if losses and max(losses) > max(1.0, losses[0]) * diverge_ratio:
            return {"symptom": "diverged",
                    "reason": f"peak loss {max(losses):.3g} > "
                              f"{diverge_ratio}x initial in run {i}",
                    "first_step": None,
                    "metrics": [r["final_metric"] for r in runs]}
    seqs = [tuple(t["param_hash"] for t in r["telemetry"]) for r in runs]
    if len(set(seqs)) > 1:
        first = None
        for i, hashes in enumerate(zip(*seqs)):
            if len(set(hashes)) > 1:
                first = i
                break
        if first is None:  # same prefix, different lengths
            first = min(len(s) for s in seqs)
        return {"symptom": "non_reproducible",
                "reason": "parameter hashes differ across same-seed runs at "
                          f"step {first}",
                "first_step": first,
                "metrics": [r["final_metric"] for r in runs]}
    return {"symptom": "healthy",
            "reason": "hashes identical across runs; losses finite",
            "first_step": None,
            "metrics": [r["final_metric"] for r in runs]}
