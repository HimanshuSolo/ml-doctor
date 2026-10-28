"""Budget: ledger, cap, kill switch, live gating."""
import json
import os

import pytest

from mldoctor.budget import Budget, BudgetExceeded, LiveDisabled


def test_record_and_ledger_file(tmp_path):
    p = str(tmp_path / "ledger.jsonl")
    b = Budget(max_calls=2, ledger_path=p)
    b.record(model="m", purpose="d", prompt_chars=3, completion_chars=4, live=False)
    assert b.call_count == 1
    assert json.loads(open(p).readline())["purpose"] == "d"


def test_cap_blocks_both_live_and_mock():
    b = Budget(max_calls=1)
    b.record(model="m", purpose="d", prompt_chars=1, completion_chars=1, live=False)
    with pytest.raises(BudgetExceeded):
        b.record(model="m", purpose="d", prompt_chars=1, completion_chars=1, live=False)


def test_live_requires_flag():
    assert Budget(live=False).call_count == 0
    with pytest.raises(LiveDisabled):
        Budget(live=False).check_live()


def test_kill_switch_blocks_live(monkeypatch):
    monkeypatch.setenv("MLDOCTOR_DISABLE_LIVE", "1")
    with pytest.raises(LiveDisabled):
        Budget(live=True).check_live()


def test_live_allowed_with_flag_no_kill(monkeypatch):
    monkeypatch.delenv("MLDOCTOR_DISABLE_LIVE", raising=False)
    Budget(live=True).check_live()
