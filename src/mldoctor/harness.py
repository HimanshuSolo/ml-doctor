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


PROJ_SEED = 20240501
SPLIT_ENV = "MLDOCTOR_SPLIT"
LR_SCALE_ENV = "MLDOCTOR_LR_SCALE"


def _grad_norm(opt):
    total = 0.0
    for group in opt.param_groups:
        for p in group["params"]:
            if p.grad is not None:
                total += float((p.grad.detach().float() ** 2).sum())
    return math.sqrt(total)


def _flat_params(opt):
    parts = [p.detach().cpu().contiguous().view(-1).float()
             for g in opt.param_groups for p in g["params"]]
    return torch.cat(parts) if parts else torch.zeros(0)


class _Projector:
    def __init__(self, dim):
        g = torch.Generator().manual_seed(PROJ_SEED)
        dirs = torch.randn(dim, 3, generator=g)
        self.dirs = dirs / dirs.norm(dim=0, keepdim=True).clamp_min(1e-12)

    def project(self, opt):
        flat = _flat_params(opt)
        if flat.numel() != self.dirs.shape[0]:
            return [None, None, None]
        vals = (flat @ self.dirs).tolist()
        return [round(float(v), 4) for v in vals]


def install_wrappers(out_path):
    """Patch Tensor.backward (scalar loss) and each optimizer instance's step
    (grad norm + param hash) via Optimizer.__init__. Patching base step is a
    no-op since SGD/Adam override it. Returns state (kept alive by child)."""
    orig_backward = torch.Tensor.backward
    orig_init = torch.optim.Optimizer.__init__
    state = {"loss": None, "step": 0, "fh": open(out_path, "w"), "proj": None}
    lr_scale = os.environ.get(LR_SCALE_ENV)
    lr_scale = float(lr_scale) if lr_scale else None

    def backward(self, *args, **kwargs):
        result = orig_backward(self, *args, **kwargs)
        if self.numel() == 1:
            state["loss"] = float(self.detach())
        return result

    def init_wrapper(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        if lr_scale is not None:
            for group in self.param_groups:
                if "lr" in group:
                    group["lr"] = group["lr"] * lr_scale
        orig_step = self.step

        @functools.wraps(orig_step)
        def step(*a, **k):
            grad_norm = _grad_norm(self)
            result = orig_step(*a, **k)
            if state["proj"] is None:
                state["proj"] = _Projector(_flat_params(self).numel())
            state["fh"].write(json.dumps({
                "step": state["step"],
                "loss": state["loss"],
                "grad_norm": grad_norm,
                "param_hash": _param_hash(self),
                "proj": state["proj"].project(self),
            }) + "\n")
            state["fh"].flush()
            state["step"] += 1
            state["loss"] = None
            return result

        self.step = step

    torch.Tensor.backward = backward
    torch.optim.Optimizer.__init__ = init_wrapper
    return state


def _install_split_hook(split_path):
    """Record train/test row-hash overlap from train_test_split calls."""
    import hashlib

    import numpy as np
    from sklearn.model_selection import train_test_split as orig_split

    def row_hashes(arr):
        try:
            a = np.asarray(arr)
            if a.ndim == 0 or a.size == 0:
                return set()
            if a.ndim == 1:
                return {hashlib.sha256(str(v).encode()).hexdigest()[:16] for v in a}
            return {hashlib.sha256(np.ascontiguousarray(a[i]).tobytes()).hexdigest()[:16]
                    for i in range(len(a))}
        except Exception:
            return set()

    state = {"done": False}

    def hooked(*args, **kwargs):
        result = orig_split(*args, **kwargs)
        if not state["done"] and args:
            try:
                n_out = 2 * (len(args) - (1 if "test_size" in kwargs or len(args) > 1 and isinstance(args[-1], float) else 0))
                parts = list(result)
                if len(parts) >= 2:
                    train_rows = set()
                    test_rows = set()
                    for j in range(0, len(parts) - 1, 2):
                        train_rows |= row_hashes(parts[j])
                        test_rows |= row_hashes(parts[j + 1])
                    overlap = len(train_rows & test_rows)
                    with open(split_path, "w") as fh:
                        json.dump({"overlap": overlap, "n_train_rows": len(train_rows),
                                   "n_test_rows": len(test_rows),
                                   "overlap_ratio": (overlap / len(test_rows) if test_rows else 0.0)},
                                  fh)
                    state["done"] = True
            except Exception:
                pass
        return result

    import sklearn.model_selection as sm
    sm.train_test_split = hooked
    return hooked


def child_main():
    threads = os.environ.get(THREADS_ENV)
    if threads:
        torch.set_num_threads(int(threads))
    if os.environ.get(DETERMINISTIC_ENV) == "1":
        torch.use_deterministic_algorithms(True)
    if os.environ.get(SPLIT_ENV):
        try:
            _install_split_hook(os.environ[SPLIT_ENV])
        except Exception:
            pass
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


_SECRET_SUBSTRINGS = ("API_KEY", "SECRET", "TOKEN", "PASSWORD", "PRIVATE_KEY")


def _is_secret_key(key):
    upper = key.upper()
    return any(part in upper for part in _SECRET_SUBSTRINGS)


def child_env(extra_env=None):
    """Allowlisted environment for target-script children.

    Secrets (any key containing API_KEY/SECRET/TOKEN/PASSWORD/PRIVATE_KEY,
    including MLDOCTOR_API_KEY) are never forwarded, even via extra_env.
    """
    keep_exact = {
        "PATH", "HOME", "LANG", "LC_ALL", "LC_LANG", "PYTHONIOENCODING",
        "PYTHONHOME", "VIRTUAL_ENV", "CONDA_PREFIX",
        "TMPDIR", "TEMP", "TMP",
        "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH",
        "SYSTEMROOT", "WINDIR",
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "CUDA_VISIBLE_DEVICES",
    }
    keep_prefixes = ("PYTHON", "TORCH_", "CUDA_", "OMP_", "MKL_", "OPENBLAS_",
                     "HF_", "HUGGINGFACE_")
    env = {}
    for key, val in os.environ.items():
        if _is_secret_key(key):
            continue
        if key in keep_exact or key.startswith(keep_prefixes):
            env[key] = val
        elif key.startswith("MLDOCTOR_") and key not in (
                CHILD_ENV, TARGET_ENV, OUT_ENV, SEED_ENV,
                THREADS_ENV, DETERMINISTIC_ENV):
            # Forward harmless MLDOCTOR_* config, never secrets (already cut).
            env[key] = val
    if extra_env:
        for key, val in extra_env.items():
            if _is_secret_key(key):
                continue
            env[key] = val
    return env


def run_script(target, telemetry_path, seed=0, timeout=120, extra_env=None):
    """Run target under wrappers. Returns dict with returncode, stdout,
    stderr, telemetry rows, final_metric (or None), and split overlap record."""
    env = child_env(extra_env)
    split_path = os.path.abspath(telemetry_path) + ".split.json"
    env.update({
        CHILD_ENV: "1",
        TARGET_ENV: os.path.abspath(target),
        OUT_ENV: os.path.abspath(telemetry_path),
        SEED_ENV: str(seed),
        SPLIT_ENV: split_path,
    })
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
                "final_metric": None, "split": None}
    rows = []
    if os.path.exists(telemetry_path):
        with open(telemetry_path) as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    split = None
    if os.path.exists(split_path):
        try:
            with open(split_path) as fh:
                split = json.load(fh)
        except Exception:
            split = None
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "telemetry": rows,
        "final_metric": _parse_metric(proc.stdout),
        "split": split,
    }
