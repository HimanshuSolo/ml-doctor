"""Full pipeline: baseline -> diagnose -> patch -> verify. Mock by default."""
import difflib
import os

from .budget import Budget
from .events import EventBus
from .llm import MockClient
from .patch import diagnose_and_patch
from .runner import classify, run_baseline
from .verify import required_runs, verify_fix


def make_diff(original, patched):
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile="original.py", tofile="patched.py"))


def run_pipeline(script, client=None, bus=None, k=5, verify_k=None, seed=0,
                 timeout=180, out_path=None, jobs=1):
    bus = bus or EventBus()
    client = client or MockClient(budget=Budget())
    mock = type(client).__name__ == "MockClient"
    with open(script) as fh:
        source = fh.read()
    bus.emit("pipeline_started", script=str(script), mock=mock)
    runs = run_baseline(script, k=k, seed=seed, timeout=timeout, jobs=jobs)
    cls = classify(runs)
    bus.emit("baseline_completed", symptom=cls["symptom"], reason=cls["reason"],
             metrics=cls["metrics"], runs=len(runs), first_step=cls.get("first_step"))
    summary = {"script": str(script), "classification": cls, "diagnosis": None,
               "patch": None, "patched_path": None, "diff": "", "verification": None,
               "passed": cls["symptom"] == "healthy", "mock": mock,
               "llm_calls": client.budget.call_count}
    if cls["symptom"] == "healthy":
        bus.emit("pipeline_completed", passed=True, verdict="healthy (no fix needed)")
        return summary
    if cls["symptom"] == "error":
        bus.emit("pipeline_completed", passed=False, verdict="error (no fix attempted)")
        return summary
    diagnosis, patch, patched = diagnose_and_patch(cls, source, client)
    summary.update(diagnosis=diagnosis, patch=patch, diff=make_diff(source, patched))
    bus.emit("diagnosed", diagnosis=diagnosis)
    bus.emit("patch_proposed", patch=patch)
    out_path = out_path or os.path.splitext(str(script))[0] + ".patched.py"
    with open(out_path, "w") as fh:
        fh.write(patched)
    summary["patched_path"] = str(out_path)
    bus.emit("patch_applied", patched_path=str(out_path), diff=summary["diff"])
    vk = verify_k or required_runs(cls["symptom"])
    bus.emit("verification_started", k=vk, required_k=required_runs(cls["symptom"]))
    ver = verify_fix(str(out_path), cls["symptom"], k=vk, seed=seed,
                     timeout=timeout, original_text=source)
    summary["verification"] = ver
    summary["passed"] = bool(ver["passed"])
    summary["llm_calls"] = client.budget.call_count
    bus.emit("verification_completed", **ver, verdict="PASS" if ver["passed"] else "FAIL")
    bus.emit("pipeline_completed", passed=summary["passed"],
             verdict="PASS" if summary["passed"] else "FAIL")
    return summary


def format_summary(s):
    c = s["classification"]
    lines = [f"symptom: {c['symptom']} — {c['reason']}",
             f"mode: {'MOCK' if s['mock'] else 'LIVE'} | llm_calls: {s['llm_calls']}"]
    if s.get("diagnosis"):
        d = s["diagnosis"]
        lines.append(f"hypothesis: {d['culprit']} — {d['fix_plan']}")
    if s.get("patch"):
        lines.append(f"patch: {s['patch']['rationale']} -> {s.get('patched_path')}")
    v = s.get("verification")
    if v:
        lines.append(f"verification: {'PASS' if v['passed'] else 'FAIL'} "
                     f"({v['k']} runs, symptom={v['symptom']}) {v['reason']}")
    else:
        lines.append(f"verdict: {'PASS' if s['passed'] else 'FAIL'}")
    return "\n".join(lines)
