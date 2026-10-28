"""Diagnose + patch: strict validation, full loop on mock (no network)."""
import json
import os

import pytest

from mldoctor.budget import Budget
from mldoctor.diagnose import ValidationError as DValidationError
from mldoctor.diagnose import diagnose, parse_diagnosis
from mldoctor.llm import MockClient
from mldoctor.patch import PatchError, apply_patch, diagnose_and_patch, parse_patch

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")

GOOD_D = {"symptom": "diverged", "reason": "r", "culprit": "c", "fix_plan": "f"}
GOOD_P = {"path": "a.py", "edits": [{"old": "x=1", "new": "x=2"}], "rationale": "r"}


def test_parse_diagnosis_valid():
    assert parse_diagnosis(json.dumps(GOOD_D))["symptom"] == "diverged"


def test_parse_diagnosis_rejects_extra_missing_bad():
    bad_extra = dict(GOOD_D, extra="z")
    with pytest.raises(DValidationError):
        parse_diagnosis(json.dumps(bad_extra))
    bad_missing = dict(GOOD_D)
    del bad_missing["reason"]
    with pytest.raises(DValidationError):
        parse_diagnosis(json.dumps(bad_missing))
    with pytest.raises(DValidationError):
        parse_diagnosis(json.dumps(dict(GOOD_D, symptom="nope")))
    with pytest.raises(DValidationError):
        parse_diagnosis(json.dumps(dict(GOOD_D, reason=123)))
    with pytest.raises(DValidationError):
        parse_diagnosis("not json")


def test_parse_patch_valid_and_strict():
    assert parse_patch(json.dumps(GOOD_P))["edits"][0]["new"] == "x=2"
    with pytest.raises(Exception):
        parse_patch(json.dumps(dict(GOOD_P, extra=1)))
    with pytest.raises(Exception):
        parse_patch(json.dumps(dict(GOOD_P, edits=[])))
    with pytest.raises(Exception):
        parse_patch(json.dumps({"path": "a", "edits": [{"old": "x"}], "rationale": "r"}))


def test_apply_patch_requires_exactly_once():
    assert apply_patch("x=1\n", GOOD_P) == "x=2\n"
    with pytest.raises(PatchError):
        apply_patch("y=0\n", GOOD_P)
    with pytest.raises(PatchError):
        apply_patch("x=1\nx=1\n", GOOD_P)


def test_full_loop_repro_on_default_mock():
    src = open(os.path.join(FIX, "repro.py")).read()
    cls = {"symptom": "non_reproducible", "reason": "hashes differ"}
    client = MockClient(budget=Budget(max_calls=4))
    d, p, patched = diagnose_and_patch(cls, src, client)
    assert d["symptom"] == "non_reproducible"
    assert "random.seed(SEED)" in patched
    assert client.budget.call_count == 2


def test_full_loop_diverge_custom_mock():
    src = open(os.path.join(FIX, "diverge.py")).read()
    cls = {"symptom": "diverged", "reason": "peak loss"}
    responses = {
        "diagnose": json.dumps({"symptom": "diverged", "reason": "lr high",
                                 "culprit": "LR=5 raw pixels", "fix_plan": "lr 0.05 scale"}),
        "patch": json.dumps({"path": "diverge.py",
                             "edits": [{"old": "LR = 5.0", "new": "LR = 0.05"}],
                             "rationale": "lower lr"}),
    }
    client = MockClient(budget=Budget(max_calls=4), responses=responses)
    d, p, patched = diagnose_and_patch(cls, src, client)
    assert "LR = 0.05" in patched
    assert diagnose(cls, src, MockClient(responses=responses))["symptom"] == "diverged"
