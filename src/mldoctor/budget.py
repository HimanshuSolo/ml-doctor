"""Per-run LLM budget: ledger, call cap, kill switch, live gating.

Live calls require explicit opt-in (Budget(live=True), wired to CLI --live)
and are blocked when MLDOCTOR_DISABLE_LIVE=1. Mock calls are offline and
always allowed but still count toward the cap.
"""
import json
import os

KILL_ENV = "MLDOCTOR_DISABLE_LIVE"


class BudgetError(Exception):
    pass


class BudgetExceeded(BudgetError):
    pass


class LiveDisabled(BudgetError):
    pass


def kill_switch_active():
    return os.environ.get(KILL_ENV) == "1"


class Budget:
    def __init__(self, max_calls=8, live=False, ledger_path=None):
        self.max_calls = max_calls
        self.live = live
        self.ledger_path = ledger_path
        self.calls = []

    @property
    def call_count(self):
        return len(self.calls)

    def check_live(self):
        if kill_switch_active():
            raise LiveDisabled(f"kill switch {KILL_ENV}=1 blocks live calls")
        if not self.live:
            raise LiveDisabled("live calls require --live")

    def check_cap(self):
        if len(self.calls) >= self.max_calls:
            raise BudgetExceeded(f"call cap {self.max_calls} exceeded")

    def record(self, *, model, purpose, prompt_chars, completion_chars, live,
               usage_total=None, usage_prompt=None, usage_completion=None,
               usage_reasoning=None):
        self.check_cap()
        entry = {
            "seq": len(self.calls),
            "model": model,
            "purpose": purpose,
            "prompt_chars": prompt_chars,
            "completion_chars": completion_chars,
            "live": live,
            "usage_total": usage_total,
            "usage_prompt": usage_prompt,
            "usage_completion": usage_completion,
            "usage_reasoning": usage_reasoning,
        }
        self.calls.append(entry)
        if self.ledger_path:
            with open(self.ledger_path, "a") as fh:
                fh.write(json.dumps(entry) + "\n")
        return entry
