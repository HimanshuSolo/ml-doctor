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


def test_chunk_source_covers_whole_file_with_overlap():
    from mldoctor.diagnose import CHUNK_OVERLAP, CHUNK_WINDOW, chunk_source
    big = "x = 1\n" * 2000  # 12000 chars
    wins = chunk_source(big)
    assert len(wins) > 1
    assert wins[0][1] == 0 and wins[-1][2].endswith("x = 1\n")
    for (i, s1, t1), (j, s2, t2) in zip(wins, wins[1:]):
        assert j == i + 1 and s2 - s1 == CHUNK_WINDOW - CHUNK_OVERLAP
        assert t1[-(CHUNK_OVERLAP):] in t2  # boundary fully seen by next window
    assert chunk_source("tiny") == [(0, 0, "tiny")]


def test_diagnose_large_single_path_for_small_source():
    from mldoctor.diagnose import diagnose_large
    from mldoctor.llm import MockClient
    client = MockClient(budget=Budget(max_calls=8))
    d, hot = diagnose_large({"symptom": "non_reproducible", "reason": "r"}, "x=1", client)
    assert d["symptom"] == "non_reproducible" and len(hot) == 1
    assert client.budget.call_count == 1  # unchanged single-shot cost


def test_diagnose_large_scans_late_windows_and_merges():
    import json as _json
    from mldoctor import diagnose as _dg
    from mldoctor.budget import Budget
    from mldoctor.llm import MockClient
    big = ("# filler line\n" * 400) + "random.shuffle(idx)  # the real bug is here\n" + ("# filler\n" * 400)
    seen_prompts = []
    orig = MockClient.complete
    def fake(self, prompt, *, purpose="diagnose", model="mock"):
        seen_prompts.append((purpose, prompt))
        if purpose == "diagnose_chunk":
            import re as _re
            idx = int(_re.search(r"window (\d+)/", prompt).group(1)) - 1
            has_bug = "the real bug" in prompt
            out = _json.dumps({"window": idx, "suspects": ["unseeded shuffle"] if has_bug else ["none"]})
        else:
            out = _json.dumps({"symptom": "non_reproducible", "reason": "merged",
                               "culprit": "window 1 holds it", "fix_plan": "seed it"})
        self.budget.record(model=model, purpose=purpose, prompt_chars=len(prompt),
                           completion_chars=len(out), live=False)
        return out
    MockClient.complete = fake
    try:
        client = MockClient(budget=Budget(max_calls=8))
        d, hot = _dg.diagnose_large({"symptom": "non_reproducible", "reason": "r"}, big, client)
    finally:
        MockClient.complete = orig
    chunk_prompts = [p for pur, p in seen_prompts if pur == "diagnose_chunk"]
    assert any("the real bug" in p for p in chunk_prompts)  # late window was seen
    merge = [p for pur, p in seen_prompts if pur == "diagnose"][0]
    assert "unseeded shuffle" in merge and "scanned" in merge
    assert d["culprit"] == "window 1 holds it"
    assert client.budget.call_count == len(chunk_prompts) + 1


def test_diagnose_large_degrades_to_single_shot_without_budget():
    from mldoctor.diagnose import diagnose_large
    from mldoctor.llm import MockClient
    from mldoctor.budget import Budget
    big = "y\n" * 3000
    client = MockClient(budget=Budget(max_calls=1))
    d, hot = diagnose_large({"symptom": "healthy", "reason": "r"}, big, client)
    assert d["symptom"] == "non_reproducible"  # mock canned reply, 1 call only
    assert client.budget.call_count == 1


def test_diagnose_large_even_spacing_covers_head_and_tail():
    import json as _json
    from mldoctor import diagnose as _dg
    from mldoctor.budget import Budget
    from mldoctor.llm import MockClient
    body = "".join("line %04d filler filler filler filler\n" % i for i in range(900))
    big = "HEAD-MARKER\n" + body + "TAIL-MARKER-random.shuffle(idx)\n"
    assert len(big) > 20000  # ~6 windows; budget allows only 3 + merge
    seen = []
    orig = MockClient.complete
    def fake(self, prompt, *, purpose="diagnose", model="mock"):
        seen.append((purpose, prompt))
        if purpose == "diagnose_chunk":
            import re as _re
            idx = int(_re.search(r"window (\d+)/", prompt).group(1)) - 1
            out = _json.dumps({"window": idx, "suspects": ["s"]})
        else:
            out = _json.dumps({"symptom": "non_reproducible", "reason": "m",
                               "culprit": "tail window", "fix_plan": "seed it"})
        self.budget.record(model=model, purpose=purpose, prompt_chars=len(prompt),
                           completion_chars=len(out), live=False)
        return out
    MockClient.complete = fake
    try:
        client = MockClient(budget=Budget(max_calls=4))
        d, hot = _dg.diagnose_large({"symptom": "non_reproducible", "reason": "r"}, big, client)
    finally:
        MockClient.complete = orig
    chunks = [p for pur, p in seen if pur == "diagnose_chunk"]
    assert len(chunks) == 3 and client.budget.call_count == 4
    assert any("HEAD-MARKER" in p for p in chunks)  # first window kept
    assert any("TAIL-MARKER" in p for p in chunks)  # last window kept
    assert d["culprit"] == "tail window"
