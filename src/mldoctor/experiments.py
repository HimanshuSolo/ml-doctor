"""Fixed experiment menu: the program runs experiments; the model only picks an id."""
import math

from .harness import DETERMINISTIC_ENV, THREADS_ENV
from .runner import run_baseline

# overfit_one_batch intentionally omitted: it cannot be done reliably without
# editing/target hooks that change optimization semantics. See PROGRESS.md.
MENU = ("first_divergence_step", "single_thread", "deterministic_algorithms",
        "lower_lr_x0.1", "initial_loss_vs_ln_classes", "grad_stats_first_steps")


def _losses(run):
    return [t["loss"] for t in run["telemetry"] if t.get("loss") is not None]


def _first_step(runs):
    seqs = [tuple(t["param_hash"] for t in r["telemetry"]) for r in runs]
    for i, hs in enumerate(zip(*seqs)):
        if len(set(hs)) > 1:
            return i
    return None if len(set(seqs)) <= 1 else min(len(s) for s in seqs)


def first_divergence_step(script, seed=0, timeout=120, runs=None):
    runs = runs or run_baseline(script, k=2, seed=seed, timeout=timeout)
    first = _first_step(runs)
    return {"experiment": "first_divergence_step", "first_step": first,
            "identical": first is None, "n_steps": [len(r["telemetry"]) for r in runs]}


def single_thread(script, seed=0, timeout=120):
    from .harness import run_script
    import os, tempfile
    tmp = tempfile.mkdtemp(prefix="mldoctor_")
    base = run_baseline(script, k=1, seed=seed, timeout=timeout)[0]
    solo = run_script(script, os.path.join(tmp, "t.jsonl"), seed=seed,
                      timeout=timeout, extra_env={THREADS_ENV: "1"})
    same = [t["param_hash"] for t in base["telemetry"]] == \
           [t["param_hash"] for t in solo["telemetry"]]
    return {"experiment": "single_thread", "hash_equal_single_thread": same,
            "base_crashed": base["returncode"] != 0, "threaded_crashed": solo["returncode"] != 0}


def deterministic_algorithms(script, seed=0, timeout=120):
    from .harness import run_script
    import os, tempfile
    tmp = tempfile.mkdtemp(prefix="mldoctor_")
    run = run_script(script, os.path.join(tmp, "d.jsonl"), seed=seed,
                     timeout=timeout, extra_env={DETERMINISTIC_ENV: "1"})
    op = None
    if run["returncode"] != 0:
        tail = [l for l in (run["stderr"] or "").splitlines() if "deterministic" in l.lower()
                or "does not have a deterministic" in l]
        op = (tail[0].strip()[:200] if tail else run["stderr"].strip().splitlines()[-1:][0][:200])
    return {"experiment": "deterministic_algorithms", "raising": run["returncode"] != 0,
            "op": op, "returncode": run["returncode"]}


def lower_lr_x0_1(script, seed=0, timeout=120):
    from .harness import run_script
    import os, tempfile
    tmp = tempfile.mkdtemp(prefix="mldoctor_")
    run = run_script(script, os.path.join(tmp, "l.jsonl"), seed=seed,
                     timeout=timeout, extra_env={"MLDOCTOR_LR_SCALE": "0.1"})
    ls = _losses(run)
    finite = all(math.isfinite(x) for x in ls)
    peak = max([x for x in ls if math.isfinite(x)], default=None)
    return {"experiment": "lower_lr_x0.1", "lr_scaled": True, "finite": finite,
            "initial_loss": ls[0] if ls else None, "peak_loss": peak,
            "final_loss": ls[-1] if ls else None, "returncode": run["returncode"]}


def initial_loss_vs_ln_classes(script, seed=0, timeout=120, runs=None, n_classes=10):
    runs = runs or run_baseline(script, k=1, seed=seed, timeout=timeout)
    ls = _losses(runs[0]) if runs else []
    init = ls[0] if ls else None
    return {"experiment": "initial_loss_vs_ln_classes", "initial_loss": init,
            "ln_classes": math.log(n_classes), "ratio": (init / math.log(n_classes)
            if init is not None else None), "n_classes": n_classes}


def grad_stats_first_steps(script, seed=0, timeout=120, runs=None, n_steps=5):
    runs = runs or run_baseline(script, k=1, seed=seed, timeout=timeout)
    grads = [t["grad_norm"] for t in (runs[0]["telemetry"] if runs else [])
             if t.get("grad_norm") is not None][:n_steps]
    finite = [g for g in grads if math.isfinite(g)]
    return {"experiment": "grad_stats_first_steps", "n": len(grads),
            "max_abs_grad": max(finite) if finite else None,
            "any_nonfinite": any(not math.isfinite(g) for g in grads),
            "grad_first_steps": grads}


_DISPATCH = {
    "first_divergence_step": lambda s, seed, to, runs: first_divergence_step(s, seed, to, runs),
    "single_thread": lambda s, seed, to, runs: single_thread(s, seed, to),
    "deterministic_algorithms": lambda s, seed, to, runs: deterministic_algorithms(s, seed, to),
    "lower_lr_x0.1": lambda s, seed, to, runs: lower_lr_x0_1(s, seed, to),
    "initial_loss_vs_ln_classes": lambda s, seed, to, runs: initial_loss_vs_ln_classes(s, seed, to, runs),
    "grad_stats_first_steps": lambda s, seed, to, runs: grad_stats_first_steps(s, seed, to, runs),
}


def run_experiment(script, experiment_id, seed=0, timeout=120, runs=None):
    if experiment_id not in _DISPATCH:
        raise ValueError(f"unknown experiment: {experiment_id}")
    return _DISPATCH[experiment_id](script, seed, timeout, runs)
