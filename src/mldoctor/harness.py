"""Run a target training script in a subprocess with telemetry wrappers.

Parent side: run_script() launches the child. Child side (MLDOCTOR_CHILD=1):
applies env controls, wraps Tensor.backward / Optimizer.step to record per-step
telemetry as JSON lines, then executes the target via runpy. Target code is
never modified. The child does NOT seed RNGs: scripts seed themselves from
MLDOCTOR_SEED, so unseeded-RNG bugs are not masked.
"""
import functools
import json
import math
import os
import re
import runpy
import subprocess
import sys

import torch

CHILD_ENV = "MLDOCTOR_CHILD"
TARGET_ENV = "MLDOCTOR_TARGET"
OUT_ENV = "MLDOCTOR_TELEMETRY"
SEED_ENV = "MLDOCTOR_SEED"
THREADS_ENV = "MLDOCTOR_THREADS"
DETERMINISTIC_ENV = "MLDOCTOR_DETERMINISTIC"
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HASH_LEN = 16
_METRIC_RE = re.compile(r"FINAL metric=(\S+)")


def _param_hash(opt):
    import hashlib

    h = hashlib.sha256()
    for group in opt.param_groups:
        for p in group["params"]:
            flat = p.detach().cpu().contiguous().view(torch.uint8).flatten().tolist()
            h.update(json.dumps(flat).encode())
    return h.hexdigest()[:_HASH_LEN]


def _grad_norm(opt):
    total = 0.0
    for group in opt.param_groups:
        for p in group["params"]:
            if p.grad is not None:
                total += float((p.grad.detach().float() ** 2).sum())
    return math.sqrt(total)


def install_wrappers(out_path):
    """Patch Tensor.backward (scalar loss) and each optimizer instance's step
    (grad norm + param hash) via Optimizer.__init__. Patching base step is a
    no-op since SGD/Adam override it. Returns state (kept alive by child)."""
    orig_backward = torch.Tensor.backward
    orig_init = torch.optim.Optimizer.__init__
    state = {"loss": None, "step": 0, "fh": open(out_path, "w")}

    def backward(self, *args, **kwargs):
        result = orig_backward(self, *args, **kwargs)
        if self.numel() == 1:
            state["loss"] = float(self.detach())
        return result

    def init_wrapper(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        orig_step = self.step

        @functools.wraps(orig_step)
        def step(*a, **k):
            grad_norm = _grad_norm(self)
            result = orig_step(*a, **k)
            state["fh"].write(json.dumps({
                "step": state["step"],
                "loss": state["loss"],
                "grad_norm": grad_norm,
                "param_hash": _param_hash(self),
            }) + "\n")
            state["fh"].flush()
            state["step"] += 1
            state["loss"] = None
            return result

        self.step = step

    torch.Tensor.backward = backward
    torch.optim.Optimizer.__init__ = init_wrapper
    return state


def child_main():
    threads = os.environ.get(THREADS_ENV)
    if threads:
        torch.set_num_threads(int(threads))
    if os.environ.get(DETERMINISTIC_ENV) == "1":
        torch.use_deterministic_algorithms(True)
    install_wrappers(os.environ[OUT_ENV])
    runpy.run_path(os.environ[TARGET_ENV], run_name="__main__")


def _parse_metric(stdout):
    match = _METRIC_RE.search(stdout or "")
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def run_script(target, telemetry_path, seed=0, timeout=120, extra_env=None):
    """Run target under wrappers. Returns dict with returncode, stdout,
    stderr, telemetry rows, and final_metric (or None). Fails once, no retry."""
    env = dict(os.environ)
    env.update({
        CHILD_ENV: "1",
        TARGET_ENV: os.path.abspath(target),
        OUT_ENV: os.path.abspath(telemetry_path),
        SEED_ENV: str(seed),
    })
    if extra_env:
        env.update(extra_env)
    env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "-c", "from mldoctor.harness import child_main; child_main()"],
            env=env, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        rows = []
        if os.path.exists(telemetry_path):
            with open(telemetry_path) as fh:
                rows = [json.loads(line) for line in fh if line.strip()]
        out = exc.stdout.decode(errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return {"returncode": 124, "stdout": out,
                "stderr": f"timeout after {timeout}s", "telemetry": rows,
                "final_metric": None}
    rows = []
    if os.path.exists(telemetry_path):
        with open(telemetry_path) as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "telemetry": rows,
        "final_metric": _parse_metric(proc.stdout),
    }
