"""Stage B: experiment menu result shapes, 3-cap, malformed rejected, no retry."""
import json

import pytest

from mldoctor.budget import Budget
from mldoctor.diagnose import ValidationError, parse_investigate
from mldoctor.experiments import MENU, run_experiment
from mldoctor.llm import MockClient

RUN = {"returncode": 0, "telemetry": [
    {"step": 0, "loss": 2.4, "grad_norm": 1.5, "param_hash": "aa", "proj": [0.1, 0.2, 0.3]},
    {"step": 1, "loss": 1.2, "grad_norm": 0.5, "param_hash": "bb", "proj": [0.2, 0.1, 0.3]}],
    "final_metric": 0.9, "split": None}
RUN2 = {"returncode": 0, "telemetry": [
    {"step": 0, "loss": 2.4, "grad_norm": 1.5, "param_hash": "aa", "proj": [0.1, 0.2, 0.3]},
    {"step": 1, "loss": 1.3, "grad_norm": 9.0, "param_hash": "XX", "proj": [0.9, 0.1, 0.3]}],
    "final_metric": 0.8, "split": None}


def test_menu_and_result_shapes():
    assert "overfit_one_batch" not in MENU and len(MENU) == 6
    out = run_experiment("x.py", "initial_loss_vs_ln_classes", runs=[RUN])
    assert out["experiment"] == "initial_loss_vs_ln_classes" and out["initial_loss"] == 2.4
    assert abs(out["ln_classes"] - 2.302585) < 1e-5
    g = run_experiment("x.py", "grad_stats_first_steps", runs=[RUN, RUN2])
    assert g["n"] == 2 and g["grad_first_steps"] == [1.5, 0.5]
    f = run_experiment("x.py", "first_divergence_step", runs=[RUN, RUN2])
    assert f["first_step"] == 1 and f["identical"] is False


def test_parse_investigate_strict():
    good = {"ranked_hypotheses": ["a"], "next_experiment": "ready_to_patch"}
    assert parse_investigate(json.dumps(good))["next_experiment"] == "ready_to_patch"
    with pytest.raises(ValidationError):
        parse_investigate(json.dumps({"ranked_hypotheses": [], "next_experiment": "x"}))
    with pytest.raises(ValidationError):
        parse_investigate(json.dumps({"ranked_hypotheses": ["a"], "next_experiment": "bogus"}))
    with pytest.raises(ValidationError):
        parse_investigate("not json")


def test_mock_investigate_roundtrip_and_cap_client():
    c = MockClient(budget=Budget(max_calls=3))
    first = json.loads(c.complete("symptom=diverged reason=x\n", purpose="investigate"))
    assert first["next_experiment"] in MENU
    second = json.loads(c.complete(
        "symptom=diverged experiment_result={\"experiment\": \"grad_stats\"}", purpose="investigate"))
    assert second["next_experiment"] == "ready_to_patch"
    assert c.budget.call_count == 2
