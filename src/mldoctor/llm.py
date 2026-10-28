"""LLM clients: MockClient (offline) and OpenAICompatibleClient (live-gated).

Text-only. Image input and Baseten-specific request details are pending
Baseten docs from the user; do not guess them here.
"""
import json
import os
import re
import urllib.error
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

# Keyed by symptom class: each fixture class gets a fitting mock fix.
MOCK_BY_SYMPTOM = {
    "non_reproducible": {"diagnosis": MOCK_DIAGNOSIS, "patch": MOCK_PATCH},
    "diverged": {
        "diagnosis": json.dumps({
            "symptom": "diverged",
            "reason": "mock: LR far too high on unnormalized inputs",
            "culprit": "LR = 5.0 with raw 0-16 pixel values, no normalization",
            "fix_plan": "lower LR to 0.05 and StandardScaler-normalize inputs",
        }),
        "patch": json.dumps({
            "path": "diverge.py",
            "edits": [
                {"old": "from sklearn.model_selection import train_test_split",
                 "new": "from sklearn.model_selection import train_test_split\nfrom sklearn.preprocessing import StandardScaler"},
                {"old": "LR = 5.0  # BUG: far too high, combined with raw 0-16 pixel values below.",
                 "new": "LR = 0.05  # lowered from 5.0: sane LR for normalized inputs"},
                {"old": "    # BUG: raw pixel values 0-16, no normalization.\n    xtr_t = torch.tensor(xtr, dtype=torch.float32)",
                 "new": "    scaler = StandardScaler().fit(xtr)\n    xtr_t = torch.tensor(scaler.transform(xtr), dtype=torch.float32)"},
                {"old": "    xte_t = torch.tensor(xte, dtype=torch.float32)",
                 "new": "    xte_t = torch.tensor(scaler.transform(xte), dtype=torch.float32)"}],
            "rationale": "mock: sane lr plus input normalization",
        }),
    },
}


def _symptom_from_prompt(prompt):
    m = re.search(r"symptom=(\w+)", prompt or "")
    return m.group(1) if m else None


class MockClient:
    """Deterministic offline client. Records to budget, never needs --live."""

    def __init__(self, budget=None, responses=None):
        self.budget = budget or Budget()
        self.responses = responses or {}

    def complete(self, prompt, *, purpose="diagnose", model="mock"):
        out = self.responses.get(purpose)
        if out is None:
            keyed = MOCK_BY_SYMPTOM.get(_symptom_from_prompt(prompt) or "", {})
            kind = "patch" if purpose == "patch" else "diagnosis"
            out = keyed.get(kind) or (MOCK_PATCH if purpose == "patch" else MOCK_DIAGNOSIS)
        self.budget.record(model=model, purpose=purpose,
                           prompt_chars=len(prompt), completion_chars=len(out),
                           live=False)
        return out


DEFAULT_BASE_URL = "https://inference.baseten.co/v1"


def load_dotenv(path=None):
    """Load KEY=VALUE lines from .env (cwd by default) into os.environ.

    Stdlib only; existing environment wins; values are never printed.
    """
    path = path or os.path.join(os.getcwd(), ".env")
    if not os.path.isfile(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip().removeprefix("export "), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            os.environ.setdefault(key.strip(), val)


class OpenAICompatibleClient:
    """OpenAI-style POST {base_url}/chat/completions over stdlib urllib.

    Baseten Model APIs (docs.baseten.co): Bearer auth, `max_tokens`,
    usage {prompt,completion,total}_tokens, reasoning in a separate
    `reasoning_content` field (final answer stays in `content`).
    Requires budget.check_live() (--live, no kill switch). No retries.
    Env: MLDOCTOR_BASE_URL, MLDOCTOR_API_KEY (or BASETEN_API_KEY),
    MLDOCTOR_MODEL, MLDOCTOR_AUTH_SCHEME (default Bearer). Key never logged.
    """

    def __init__(self, *, base_url, model, budget, api_key=None, timeout=30,
                 auth_scheme="Bearer", max_tokens=1024):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.budget = budget
        self.api_key = api_key
        self.timeout = timeout
        self.auth_scheme = auth_scheme
        self.max_tokens = max_tokens

    @classmethod
    def from_env(cls, budget, **kw):
        load_dotenv()
        base = (os.environ.get("MLDOCTOR_BASE_URL")
                or os.environ.get("BASETEN_BASE_URL") or DEFAULT_BASE_URL)
        model = os.environ.get("MLDOCTOR_MODEL")
        if not model:
            raise LLMError("MLDOCTOR_MODEL must be set for --live")
        return cls(base_url=base, model=model, budget=budget,
                   api_key=(os.environ.get("MLDOCTOR_API_KEY")
                            or os.environ.get("BASETEN_API_KEY")),
                   auth_scheme=os.environ.get("MLDOCTOR_AUTH_SCHEME", "Bearer"), **kw)

    def _is_local(self):
        return "127.0.0.1" in self.base_url or "localhost" in self.base_url

    def complete(self, prompt, *, purpose="chat"):
        self.budget.check_live()
        self.budget.check_cap()
        if not self.api_key and not self._is_local():
            raise LLMError("MLDOCTOR_API_KEY is not set (required for non-local base URL)")
        body = json.dumps({"model": self.model, "max_tokens": self.max_tokens,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=body,
            headers={"Content-Type": "application/json"})
        if self.api_key:
            req.add_header("Authorization", f"{self.auth_scheme} {self.api_key}")
        try:
            if self._is_local():
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode())
            else:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode(errors="replace")[:500]
            except Exception:
                detail = ""
            raise LLMError(f"llm HTTP error {exc.code}: {detail}") from exc
        except Exception as exc:
            reason = getattr(exc, "reason", exc)
            raise LLMError(f"llm request failed: {type(exc).__name__}: {reason}") from exc
        try:
            choice = payload["choices"][0]
            out = choice["message"]["content"]
            if type(out) is not str:
                raise TypeError("content not a string")
        except (KeyError, IndexError, TypeError) as exc:
            msg = {}
            try:
                choice = payload["choices"][0]
                msg = choice.get("message") or {}
            except Exception:
                choice = None
            raise LLMError(
                "bad llm response shape: missing choices[0].message.content "
                f"(top keys: {sorted(payload.keys())}, "
                f"finish_reason: {(choice or {}).get('finish_reason')}, "
                f"has reasoning_content: {bool(msg.get('reasoning_content'))})"
            ) from exc
        usage = payload.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        msg = choice.get("message") or {}
        self.last_response_info = {
            "top_keys": sorted(payload.keys()),
            "model_reported": payload.get("model"),
            "finish_reason": choice.get("finish_reason"),
            "usage": usage,
            "has_reasoning_content": bool(msg.get("reasoning_content")),
            "reasoning_chars": len(msg.get("reasoning_content") or ""),
            "content_chars": len(out),
        }
        if not out.strip():
            raise LLMError("empty content in llm response "
                           "(reasoning may have consumed max_tokens; raise --max-tokens)")
        self.budget.record(model=self.model, purpose=purpose,
                           prompt_chars=len(prompt), completion_chars=len(out),
                           live=True, usage_total=usage.get("total_tokens"),
                           usage_prompt=usage.get("prompt_tokens"),
                           usage_completion=usage.get("completion_tokens"),
                           usage_reasoning=details.get("reasoning_tokens"))
        return out

    def complete_with_image(self, *args, **kwargs):
        raise NotImplementedError("image input pending Baseten docs")
