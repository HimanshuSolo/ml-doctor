"""Events + pipeline + terminal summary (mock, no model)."""
import os

import pytest

from mldoctor.budget import Budget
from mldoctor.events import EventBus
from mldoctor.llm import MockClient
from mldoctor.pipeline import format_summary, run_pipeline

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_bus_orders_and_notifies():
    seen = []
    bus = EventBus(listeners=[seen.append])
    bus.emit("a", x=1)
    bus.emit("b")
    assert [e["seq"] for e in bus.events] == [0, 1]
    assert seen == bus.events and bus.events[0]["x"] == 1


@pytest.mark.slow
def test_pipeline_healthy_skips_llm(tmp_path):
    s = run_pipeline(os.path.join(FIX, "healthy.py"), k=2, out_path=str(tmp_path / "p.py"))
    assert s["passed"] is True and s["diagnosis"] is None and s["llm_calls"] == 0


@pytest.mark.slow
def test_pipeline_repro_mock_end_to_end(tmp_path):
    bus = EventBus()
    out = str(tmp_path / "repro.patched.py")
    client = MockClient(budget=Budget(max_calls=4))
    s = run_pipeline(os.path.join(FIX, "repro.py"), client=client, bus=bus,
                     k=2, verify_k=2, out_path=out)
    assert s["passed"] is True and s["verification"]["k"] == 2
    assert "random.seed(SEED)" in open(out).read()
    assert [e["type"] for e in bus.events] == [
        "pipeline_started", "baseline_completed", "diagnosed", "patch_proposed",
        "patch_applied", "verification_started", "verify_progress", "verify_progress",
        "verification_completed", "pipeline_completed"]
    text = format_summary(s)
    assert "MOCK" in text and "PASS" in text and "hypothesis:" in text
