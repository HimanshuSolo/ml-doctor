"""Child env allowlist: target-script children never receive secrets."""
import os

from mldoctor import harness


def test_secrets_never_forwarded(monkeypatch):
    monkeypatch.setenv("MLDOCTOR_API_KEY", "shh")
    monkeypatch.setenv("SOME_SECRET", "shh")
    monkeypatch.setenv("MY_TOKEN", "shh")
    monkeypatch.setenv("MLDOCTOR_SEED", "should-be-overridden")
    env = harness.child_env({"MLDOCTOR_API_KEY": "shh2", "EXTRA_OK": "1"})
    for key in env:
        assert "API_KEY" not in key.upper()
        assert "SECRET" not in key.upper()
        assert "TOKEN" not in key.upper()
    assert env["EXTRA_OK"] == "1"


def test_run_script_sets_controls_not_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("MLDOCTOR_API_KEY", "shh")
    target = tmp_path / "t.py"
    target.write_text("print('FINAL metric=1.0')\n")
    tel = str(tmp_path / "tel.jsonl")
    out = harness.run_script(str(target), tel, seed=7)
    assert out["returncode"] == 0
    assert out["final_metric"] == 1.0
