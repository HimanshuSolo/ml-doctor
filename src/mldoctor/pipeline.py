"""Full pipeline: baseline -> diagnose -> patch -> verify. Mock by default."""
import difflib
import os

from .budget import Budget
from .events import EventBus
from .llm import MockClient
from .patch import diagnose_and_patch
from .runner import classify, run_baseline
from .verify import evidence_of, required_runs, verify_fix


def _tokens(client):
    return sum(c.get("usage_total") or c.get("completion_chars") or 0
               for c in client.budget.calls)


def make_diff(original, patched):
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile="original.py", tofile="patched.py"))


def run_pipeline(script, client=None, bus=None, k=5, verify_k=None, seed=0,
                 timeout=180, out_path=None, jobs=1, investigate=False,
                 vision=False, source_text=None):
    bus = bus or EventBus()
    client = client or MockClient(budget=Budget())
    mock = type(client).__name__ == "MockClient"
    if source_text is not None:
        source = source_text
    else:
        with open(script) as fh:
            source = fh.read()
    bus.emit("pipeline_started", script=str(script), mock=mock)
    runs = run_baseline(script, k=k, seed=seed, timeout=timeout, jobs=jobs)
    cls = classify(runs)
    before = evidence_of(runs)
    bus.emit("baseline_completed", symptom=cls["symptom"], reason=cls["reason"],
             metrics=cls["metrics"], runs=len(runs), first_step=cls.get("first_step"),
             evidence=before)
    summary = {"script": str(script), "classification": cls, "diagnosis": None,
               "patch": None, "patched_path": None, "diff": "", "verification": None,
               "passed": cls["symptom"] == "healthy", "mock": mock,
               "evidence": {"before": before, "after": None},
               "llm_calls": client.budget.call_count, "tokens_used": _tokens(client)}
    if cls["symptom"] == "healthy":
        bus.emit("pipeline_completed", passed=True, verdict="healthy (no fix needed)")
        return summary
    if cls["symptom"] == "error":
        bus.emit("pipeline_completed", passed=False, verdict="error (no fix attempted)")
        return summary
    image_sent = False
    if vision:
        from .plots import render_loss_png_b64
        img_b64, used = render_loss_png_b64(before)
        if used:
            # Probe the provider once with the tiny image; on rejection the
            # run proceeds text-only and says so in the report.
            try:
                from .llm import LLMError
                client.complete_with_image(
                    "Inspect this loss curve. Reply with exactly OK.",
                    __import__("base64").b64decode(img_b64))
                image_sent = True
            except Exception as exc:
                bus.emit("vision_unavailable", error=str(exc)[:300])
    if investigate:
        from .diagnose import build_investigate_prompt, parse_investigate
        from .experiments import run_experiment
        results, experiments_run = [], []
        for _ in range(3):
            plan = parse_investigate(
                client.complete(build_investigate_prompt(cls, results),
                                purpose="investigate"))
            bus.emit("hypotheses_reranked", ranked_hypotheses=plan["ranked_hypotheses"],
                     next_experiment=plan["next_experiment"])
            if plan["next_experiment"] == "ready_to_patch":
                break
            bus.emit("experiment_started", experiment=plan["next_experiment"])
            result = run_experiment(str(script), plan["next_experiment"],
                                    seed=seed, timeout=timeout, runs=runs)
            results.append(result)
            bus.emit("experiment_result", **result)
            experiments_run.append(result["experiment"])
        summary["experiments"] = results
    diagnosis, patch, patched = diagnose_and_patch(cls, source, client)
    summary["vision"] = {"requested": bool(vision), "image_sent": image_sent}
    summary.update(diagnosis=diagnosis, patch=patch, diff=make_diff(source, patched))
    bus.emit("diagnosed", diagnosis=diagnosis)
    bus.emit("patch_proposed", patch=patch)
    if out_path is None:
        stem = os.path.splitext(os.path.basename(str(script)))[0]
        out_path = os.path.join(os.getcwd(), ".mldoctor", "patched", stem + ".patched.py")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as fh:
        fh.write(patched)
    summary["patched_path"] = str(out_path)
    bus.emit("patch_applied", patched_path=str(out_path), diff=summary["diff"])
    vk = verify_k or required_runs(cls["symptom"])
    bus.emit("verification_started", k=vk, required_k=required_runs(cls["symptom"]),
             mode="seeds" if cls["symptom"] == "diverged" else "same-seed")
    _before_metric = (cls["metrics"][0] if cls.get("metrics") else None)
    ver = verify_fix(str(out_path), cls["symptom"], k=vk, seed=seed,
                     timeout=timeout, original_text=source, original_metric=_before_metric,
                     progress=lambda p: bus.emit("verify_progress", **p))
    summary["verification"] = ver
    summary["evidence"]["after"] = ver.get("evidence")
    summary["passed"] = bool(ver["passed"])
    summary["llm_calls"] = client.budget.call_count
    summary["tokens_used"] = _tokens(client)
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
        unit = "seeds" if v.get("mode") == "seeds" else "runs"
        lines.append(f"verification: {'PASS' if v['passed'] else 'FAIL'} "
                     f"({v['k']} {unit}, symptom={v['symptom']}) {v['reason']}")
    else:
        lines.append(f"verdict: {'PASS' if s['passed'] else 'FAIL'}")
    return "\n".join(lines)
