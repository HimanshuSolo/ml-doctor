"""Feasibility probe: capture per-step loss + param hash by wrapping
torch.Tensor.backward and torch.optim.Optimizer.step; check two same-seed
runs are identical. Default mode launches two wrapped subprocess runs.
Run: .venv/bin/python feasibility/harness_probe.py"""
import functools
import hashlib
import json
import math
import os
import runpy
import subprocess
import sys

import torch

MODE_ENV = "MLDOCTOR_PROBE_MODE"
OUT_ENV = "MLDOCTOR_TELEMETRY"
SEED_ENV = "MLDOCTOR_SEED"
SEED = "1234"
STEPS_EXPECTED = 15


def _param_hash(opt):
    h = hashlib.sha256()
    for group in opt.param_groups:
        for p in group["params"]:
            h.update(p.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()[:16]


def _grad_norm(opt):
    total = 0.0
    for group in opt.param_groups:
        for p in group["params"]:
            if p.grad is not None:
                total += float((p.grad.detach().cpu().float() ** 2).sum())
    return math.sqrt(total)


def install_wrappers(out_path):
    # SGD/Adam override Optimizer.step, so patching the base method is a no-op.
    # Patch Optimizer.__init__ instead to wrap each instance's step. Covers
    # custom optimizers too. Limitation: LBFGS-style closures report a
    # pre-closure grad norm.
    orig_backward = torch.Tensor.backward
    orig_init = torch.optim.Optimizer.__init__
    state = {"loss": None, "step": 0, "fh": open(out_path, "w")}

    def backward(self, *args, **kwargs):
        result = orig_backward(self, *args, **kwargs)
        if self.numel() == 1:
            state["loss"] = float(self.detach().cpu())
        return result

    def init_wrapper(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        orig_step = self.step

        @functools.wraps(orig_step)
        def step(*a, **k):
            gn = _grad_norm(self)
            result = orig_step(*a, **k)
            state["fh"].write(json.dumps({
                "step": state["step"], "loss": state["loss"],
                "grad_norm": gn, "param_hash": _param_hash(self),
            }) + "\n")
            state["fh"].flush()
            state["step"] += 1
            state["loss"] = None
            return result

        self.step = step

    torch.Tensor.backward = backward
    torch.optim.Optimizer.__init__ = init_wrapper
    return state


def wrap_main(target):
    seed = int(os.environ.get(SEED_ENV, "0"))
    torch.manual_seed(seed)
    install_wrappers(os.environ[OUT_ENV])
    runpy.run_path(target, run_name="__main__")


def run_once(tag, target):
    out = f".mldoctor_probe_{tag}.jsonl"
    env = dict(os.environ, **{MODE_ENV: "wrap", OUT_ENV: out, SEED_ENV: SEED})
    proc = subprocess.run([sys.executable, __file__, target],
                          env=env, capture_output=True, text=True, timeout=120)
    print(f"--- {tag}: exit={proc.returncode} ---")
    print(proc.stdout[-500:])
    print(proc.stderr[-500:])
    rows = [json.loads(line) for line in open(out) if line.strip()]
    os.remove(out)
    return rows


def compare(a, b):
    print(f"steps: run1={len(a)} run2={len(b)} (expected {STEPS_EXPECTED})")
    missing = [r["step"] for r in a + b if r["loss"] is None or not r["param_hash"]]
    print(f"steps missing loss/hash: {missing if missing else 'none'}")
    if not a or not b:
        print("VERDICT: NO TELEMETRY (wrappers captured nothing)")
        return
    verdict = "IDENTICAL"
    for i, (ra, rb) in enumerate(zip(a, b)):
        if ra["loss"] != rb["loss"] or ra["param_hash"] != rb["param_hash"]:
            verdict = (f"DIVERGED at step {i}: loss {ra['loss']} vs {rb['loss']}, "
                       f"hash {ra['param_hash']} vs {rb['param_hash']}")
            break
    if len(a) != len(b):
        verdict = "DIVERGED: different step counts"
    print("VERDICT:", verdict)


def main():
    if os.environ.get(MODE_ENV) == "wrap":
        wrap_main(sys.argv[1])
    else:
        print(f"torch={torch.__version__} threads={torch.get_num_threads()}")
        target = os.path.join(os.path.dirname(__file__), "tiny_model.py")
        compare(run_once("run1", target), run_once("run2", target))


if __name__ == "__main__":
    main()
