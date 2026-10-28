"""Report generator: healthy N/A, consistency, SVG evidence, usage labels."""
import os

from mldoctor.llm import MOCK_BY_SYMPTOM
from mldoctor.patch import apply_patch, parse_patch
from mldoctor.report import render_report

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def _healthy():
    return {"script": os.path.join(ROOT, "fixtures", "healthy.py"),
            "classification": {"symptom": "healthy", "reason": "hashes identical across runs; losses finite"},
            "diagnosis": None, "patch": None, "diff": "", "verification": None,
            "passed": True, "mock": True, "llm_calls": 0, "tokens_used": 0,
            "evidence": {"before": {"loss_curves": [[2.0, 1.0]], "hash_fingerprints": [["abc123", "def456"]], "metrics": [0.9]},
                         "after": None}}


def test_healthy_report_has_no_fail_or_none():
    h = render_report(_healthy())
    assert "FAIL" not in h and "None" not in h
    assert "HEALTHY (no fix needed)" in h
    assert h.count("Not applicable: no problem detected") >= 5
    assert "mock calls: 0, simulated tokens: 0" in h
    assert "/home/" not in h and "fixtures/healthy.py" in h


def test_failed_verification_shows_fail_and_verdict_agrees():
    s = _healthy()
    s.update(classification={"symptom": "non_reproducible", "reason": "hashes differ"},
             diagnosis={"culprit": "c", "fix_plan": "f"}, diff="-a\n+b", passed=False,
             verification={"passed": False, "reason": "hashes differ", "k": 2,
                           "mode": "same-seed", "seeds": [0, 0], "violations": []})
    h = render_report(s)
    assert "FAIL" in h
    ver_line = h.split("<h3>Verification</h3>")[1].split("</p>")[0]
    verdict = h.split("<b>Verdict:</b>")[1].split("|")[0]
    assert "FAIL" in ver_line and "FAIL" in verdict


def test_live_usage_not_labeled_simulated():
    s = _healthy(); s.update(mock=False, llm_calls=2, tokens_used=42)
    h = render_report(s)
    assert "simulated" not in h and "42" in h


def test_diverge_report_peak_table_hashes_and_marker():
    s = _healthy()
    s.update(classification={"symptom": "diverged", "reason": "peak too high"},
             diagnosis={"culprit": "LR", "fix_plan": "lower"}, diff="-LR = 5.0\n+LR = 0.05",
             verification={"passed": True, "reason": "finite, sane", "k": 5, "mode": "seeds",
                           "seeds": [0, 1, 2, 3, 4], "violations": []},
             evidence={"before": {"loss_curves": [[1.0, 50.0, 80.0]], "hash_fingerprints": [["aaaaaa"]], "metrics": [0.1]},
                       "after": {"loss_curves": [[2.0, 1.0]], "hash_fingerprints": [["bbbbbb"]], "metrics": [0.9]}})
    h = render_report(s)
    assert "Parameter hash fingerprints" in h
    assert "Different seeds produce different hashes by design" in h
    assert "exploded at step" in h
    assert "80" in h and "5 seeds (0-4) finite" in h
    assert "experiments" not in h.lower() or "none (single-pass diagnosis)" in h


def test_live_reply_wrapped_in_template_tokens_still_parses():
    from mldoctor.diagnose import build_prompt, parse_diagnosis
    text = '<|start|>assistant to\n{"symptom": "diverged", "reason": "r", "culprit": "c", "fix_plan": "f"}'
    assert parse_diagnosis(text)["symptom"] == "diverged"
    assert "ONLY a JSON object" in build_prompt({"symptom": "diverged", "reason": "r"}, "x = 1")


def test_mock_diverge_patch_lr_line_has_no_bug_comment():
    source = open(os.path.join(ROOT, "fixtures", "diverge.py")).read()
    patched = apply_patch(source, parse_patch(MOCK_BY_SYMPTOM["diverged"]["patch"]))
    lr_line = [l for l in patched.splitlines() if l.startswith("LR =")][0]
    assert "0.05" in lr_line and "BUG" not in lr_line
