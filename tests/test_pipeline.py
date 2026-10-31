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


BIG_REPRO_TEMPLATE = '''"""Large pipeline fixture: bug lives far below the 4000-char cutoff."""
import os, random
import numpy as np
import torch
import torch.nn as nn

SEED = int(os.environ.get("MLDOCTOR_SEED", "0"))

{FILLER}
def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    X = torch.randn(600, 20)
    y = (X.sum(1) > 0).long()
    ds = torch.utils.data.TensorDataset(X, y)
    model = nn.Sequential(nn.Linear(20, 16), nn.ReLU(), nn.Linear(16, 2))
    opt = torch.optim.SGD(model.parameters(), lr=0.05)
    loss_fn = nn.CrossEntropyLoss()
    for _ in range(3):
        idx = list(range(len(ds)))
        random.shuffle(idx)
        for s in range(0, len(idx), 64):
            xb = torch.stack([ds[i][0] for i in idx[s:s + 64]])
            yb = torch.tensor([ds[i][1] for i in idx[s:s + 64]])
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
    with torch.no_grad():
        acc = (model(X).argmax(1) == y).float().mean().item()
    print(f"FINAL metric={{acc:.4f}}", flush=True)

if __name__ == "__main__":
    main()
'''


@pytest.mark.slow
def test_pipeline_large_file_chunked_end_to_end(tmp_path):
    filler = "".join("def helper_%d():\n    return %d\n\n" % (i, i) for i in range(400))
    script = tmp_path / "big_repro.py"
    script.write_text(BIG_REPRO_TEMPLATE.format(FILLER=filler))
    assert script.stat().st_size > 12000
    bus = EventBus()
    client = MockClient(budget=Budget(max_calls=8))
    s = run_pipeline(str(script), client=client, bus=bus,
                     k=2, verify_k=2, out_path=str(tmp_path / "big.patched.py"))
    assert s["passed"] is True and s["verification"]["k"] == 2
    assert s["llm_calls"] > 3  # chunked windows + merge + patch, not single-shot
    assert "random.seed(SEED)" in open(tmp_path / "big.patched.py").read()
