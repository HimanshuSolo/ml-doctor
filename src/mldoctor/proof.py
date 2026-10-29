"""Proof bundle: reproducible record of a run (JSON + small HTML view)."""
import hashlib
import json
import os
import platform
import sys
import time

from .runner import run_baseline, classify as _classify_runs


def _sha(path_or_text):
    if path_or_text is None:
        return ""
    if os.path.isfile(path_or_text):
        with open(path_or_text, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    return hashlib.sha256(str(path_or_text).encode()).hexdigest()


def _env_fingerprint():
    try:
        import torch
        tv = torch.__version__
    except Exception:
        tv = None
    try:
        import numpy
        nv = numpy.__version__
    except Exception:
        nv = None
    try:
        import sklearn
        sv = sklearn.__version__
    except Exception:
        sv = None
    return {"python": sys.version.split()[0], "torch": tv, "numpy": nv,
            "sklearn": sv, "platform": platform.platform()}


def build_bundle(script, summary, script_text=None):
    ev = (summary.get("evidence") or {}).get("after") or {}
    runs = []
    curves = ev.get("loss_curves") or []
    fps = ev.get("hash_fingerprints") or []
    metrics = (summary.get("verification") or {}).get("metrics") or []
    for i in range(len(curves) or len(fps)):
        pts = [p for p in curves[i] if p is not None] if i < len(curves) else []
        runs.append({"run_index": i, "hash": (fps[i][-1] if i < len(fps) and fps[i] else None),
                     "peak_loss": max(pts) if pts else None,
                     "metric": metrics[i] if i < len(metrics) else None})
    return {
        "format": "mldoctor-proof/v1",
        "mode": "MOCK" if summary.get("mock") else "LIVE",
        "model": ((summary.get("diagnosis") or {}).get("model")
                  or "mock" if summary.get("mock") else None),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "script": str(script),
        "script_sha256": _sha(script) if script_text is None else _sha(script_text),
        "patch_sha256": _sha((summary.get("diff") or "").encode().hex() and summary.get("diff")),
        "seeds": (summary.get("verification") or {}).get("seeds") or [],
        "run_counts": {"verification_k": (summary.get("verification") or {}).get("k")},
        "per_run": runs,
        "verdict": (summary.get("verification") or {}).get("passed"),
        "verification_verdict": ("PASS" if (summary.get("verification") or {}).get("passed")
                                 else "FAIL" if summary.get("verification") else None),
        "verification": summary.get("verification"),
        "classification": summary.get("classification"),
        "diagnosis": summary.get("diagnosis"),
        "llm_calls": summary.get("llm_calls"), "tokens_used": summary.get("tokens_used"),
        "mock": summary.get("mock"), "vision": summary.get("vision"),
        "env": _env_fingerprint(),
    }


def bundle_html(bundle):
    rows = "".join(f"<tr><td>{r.get('run_index')}</td><td>{r.get('hash') or ''}</td>"
                   f"<td>{r.get('peak_loss')}</td><td>{r.get('metric')}</td></tr>"
                   for r in bundle.get("per_run", []))
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>MLDoctor proof</title></head><body><h1>MLDoctor proof</h1>"
            f"<p>Mode: {bundle.get('mode')} | Verdict: {bundle.get('verification_verdict')}"
            f" | Script SHA-256: {bundle.get('script_sha256')}</p>"
            f"<table border='1'><tr><th>run</th><th>hash</th><th>peak loss</th>"
            f"<th>metric</th></tr>{rows}</table></body></html>")


def write_bundle(script, summary, out_base):
    bundle = build_bundle(script, summary)
    base = out_base[:-5] if out_base.endswith(".json") else out_base
    jpath, hpath = base + ".json", base + ".html"
    with open(jpath, "w") as fh:
        json.dump(bundle, fh, indent=2, default=str)
    with open(hpath, "w") as fh:
        fh.write(bundle_html(bundle))
    return jpath, bundle


def recheck_bundle(bundle, seed=0, timeout=180):
    """Re-run verification from the bundle and compare to recorded values."""
    script = bundle.get("script")
    ok_verdict = bool(bundle.get("verification") and bundle["verification"].get("passed"))
    recorded = {(r.get("run_index"), r.get("hash")) for r in bundle.get("per_run", [])}
    now_env = _env_fingerprint()
    fingerprint_differs = now_env != bundle.get("env")
    runs = run_baseline(script, k=max(2, len(bundle.get("per_run", []) or 2)),
                        seed=seed, timeout=timeout)
    cls = _classify_runs(runs)
    mismatch = (cls["symptom"] == "healthy") != ok_verdict
    if fingerprint_differs:
        msg = ("environment fingerprint differs from the bundle; "
               "hashes may legitimately differ. "
               f"Recorded verdict {'PASS' if ok_verdict else 'FAIL'}; "
               f"recheck symptom {cls['symptom']}.")
    else:
        msg = (f"recheck symptom {cls['symptom']}; recorded verdict "
               f"{'PASS' if ok_verdict else 'FAIL'}; match={not mismatch}")
    return {"current_symptom": cls["symptom"], "recorded_verdict": ok_verdict,
            "verdict_mismatch": mismatch and not fingerprint_differs,
            "fingerprint_differs": fingerprint_differs, "message": msg}


def export_patch_file(script, summary, out_base):
    diff = summary.get("diff") or ""
    base = out_base
    if base.endswith(".patch"):
        base = base[:-6]
    patch_path = base + ".patch"
    with open(patch_path, "w") as fh:
        fh.write(diff if diff.endswith("\n") or not diff else diff + "\n")
    desc_path = base + ".md"
    diag = summary.get("diagnosis") or {}
    ver = summary.get("verification") or {}
    lines = [
        f"# MLDoctor patch: {os.path.basename(str(script))}",
        "",
        f"Mode: {'MOCK (simulated)' if summary.get('mock') else 'LIVE'}",
        f"Symptom: {(summary.get('classification') or {}).get('symptom')}",
        f"Hypothesis: {diag.get('culprit', '')} — {diag.get('fix_plan', '')}",
        f"Verification: {'PASS' if ver.get('passed') else 'FAIL'} — {ver.get('reason', '')}",
        "",
        "Applied by hand only; never pushed automatically.",
    ]
    with open(desc_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return patch_path
