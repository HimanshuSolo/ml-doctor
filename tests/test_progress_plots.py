"""Verify-progress ordering, evidence, plots, report (slow run marked)."""
import os

import pytest

from mldoctor.events import EventBus
from mldoctor.pipeline import run_pipeline
from mldoctor.plots import render_loss_png
from mldoctor.report import render_report

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_plots_png(tmp_path):
    out = render_loss_png([[2.0, 1.5, 1.0], [2.1, 1.6, 1.1]], str(tmp_path / "l.png"))
    assert open(out, "rb").read(8).startswith(b"\x89PNG")


def test_report_contains_sections():
    s = {"script": "x.py", "classification": {"symptom": "diverged", "reason": "r"},
         "diagnosis": {"culprit": "c", "fix_plan": "f"}, "diff": "-a\n+b",
         "verification": {"passed": True, "reason": "ok", "k": 5, "mode": "seeds", "seeds": [0, 1]},
         "passed": True, "mock": True, "llm_calls": 2, "tokens_used": 15,
         "evidence": {"before": {"loss_curves": [[2, 1]], "hash_fingerprints": [["abc123"]]},
                      "after": {"loss_curves": [[2, 1]], "hash_fingerprints": [["abc123"]]}}}
    h = render_report(s)
    assert "MOCK" in h and "Hypotheses" in h and "Verification" in h and "abc123" in h


@pytest.mark.slow
def test_verify_progress_ordering_end_to_end(tmp_path):
    bus = EventBus()
    s = run_pipeline(os.path.join(FIX, "repro.py"), bus=bus, k=2, verify_k=3,
                     out_path=str(tmp_path / "p.py"))
    types = [e["type"] for e in bus.events]
    prog = [e for e in bus.events if e["type"] == "verify_progress"]
    assert [(e["n_done"], e["n_total"], e["n_failed"]) for e in prog] == [(1, 3, 0), (2, 3, 0), (3, 3, 0)]
    assert types.index("verification_started") < types.index("verify_progress") < types.index("verification_completed")
    assert s["evidence"]["before"]["hash_fingerprints"]
    assert s["evidence"]["after"]["loss_curves"]
