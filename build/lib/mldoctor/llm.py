"""LLM clients: MockClient (offline) and OpenAICompatibleClient (live-gated).

Text-only. Image input and Baseten-specific request details are pending
Baseten docs from the user; do not guess them here.
"""
import json
import urllib.request

from .budget import Budget


class LLMError(Exception):
    pass


MOCK_DIAGNOSIS = json.dumps({
    "symptom": "non_reproducible",
    "reason": "mock: unseeded RNG suspected",
    "culprit": "random.shuffle without random.seed",
    "fix_plan": "seed all RNGs from MLDOCTOR_SEED",
})

MOCK_PATCH = json.dumps({
    "path": "target.py",
    "edits": [{"old": "np.random.seed(SEED)", "new": "random.seed(SEED)\n    np.random.seed(SEED)"}],
    "rationale": "mock: seed stdlib random",
})


class MockClient:
    """Deterministic offline client. Records to budget, never needs --live."""

    def __init__(self, budget=None, responses=None):
        self.budget = budget or Budget()
        self.responses = responses or {}

    def complete(self, prompt, *, purpose="diagnose", model="mock"):
        out = self.responses.get(purpose)
        if out is None:
            out = MOCK_PATCH if purpose == "patch" else MOCK_DIAGNOSIS
        self.budget.record(model=model, purpose=purpose,
                           prompt_chars=len(prompt), completion_chars=len(out),
                           live=False)
        return out


class OpenAICompatibleClient:
    """Minimal chat-completions client over stdlib urllib.

    Requires budget.check_live() (i.e. --live, no kill switch). Tests run
    only against a fake local HTTP server, never live.
    """

    def __init__(self, *, base_url, model, budget, api_key=None, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.budget = budget
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, prompt, *, purpose="chat"):
        self.budget.check_live()
        self.budget.check_cap()
        body = json.dumps({"model": self.model,
                           "messages": [{"role": "user", "content": prompt}],
                           }).encode()
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=body,
            headers={"Content-Type": "application/json"})
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            if "127.0.0.1" in self.base_url or "localhost" in self.base_url:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode())
            else:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode())
        except Exception as exc:
            raise LLMError(f"llm request failed: {exc}") from exc
        try:
            out = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"bad llm response shape: {payload!r}") from exc
        self.budget.record(model=self.model, purpose=purpose,
                           prompt_chars=len(prompt), completion_chars=len(out),
                           live=True)
        return out

    def complete_with_image(self, *args, **kwargs):
        raise NotImplementedError("image input pending Baseten docs")
