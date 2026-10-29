"""Diagnose symptom from classification + source via LLM (mock by default).

Strict stdlib validation mirrors pydantic strict + extra=forbid (pydantic
install pending approval; see assumptions). No network on mock path.
"""
import json

SYMPTOMS = ("healthy", "non_reproducible", "diverged", "error", "leakage")
_FIELDS = ("symptom", "reason", "culprit", "fix_plan")


class ValidationError(Exception):
    pass


def extract_json(text):
    """JSON object embedded in a reply: live models may wrap it in prose
    or chat-template tokens, so take the outermost {...} span."""
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if 0 <= start < end else text


def parse_diagnosis(text):
    try:
        obj = json.loads(extract_json(text))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"not JSON: {exc}") from exc
    if type(obj) is not dict:
        raise ValidationError("diagnosis must be an object")
    if set(obj) != set(_FIELDS):
        raise ValidationError(f"fields must be exactly {list(_FIELDS)}")
    if obj["symptom"] not in SYMPTOMS:
        raise ValidationError(f"bad symptom: {obj['symptom']!r}")
    for f in ("reason", "culprit", "fix_plan"):
        if type(obj[f]) is not str or not obj[f].strip():
            raise ValidationError(f"{f} must be a non-empty string")
    return obj


def build_prompt(classification, source):
    return ("Respond with ONLY a JSON object, no prose, with exactly these "
            "fields: symptom (one of healthy, non_reproducible, diverged, "
            "error), reason, culprit, fix_plan.\n"
            f"symptom={classification.get('symptom')} "
            f"reason={classification.get('reason')}\n"
            f"source:\n{source[:4000]}")


def diagnose(classification, source, client):
    return parse_diagnosis(client.complete(build_prompt(classification, source),
                                           purpose="diagnose"))


def parse_investigate(text):
    """Strict plan: ranked hypotheses + next experiment id (or ready_to_patch)."""
    from .experiments import MENU
    try:
        obj = json.loads(extract_json(text))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"not JSON: {exc}") from exc
    if type(obj) is not dict or set(obj) != {"ranked_hypotheses", "next_experiment"}:
        raise ValidationError("fields must be exactly [ranked_hypotheses, next_experiment]")
    hyps = obj["ranked_hypotheses"]
    if type(hyps) is not list or not hyps or any(type(h) is not str or not h.strip() for h in hyps):
        raise ValidationError("ranked_hypotheses must be a non-empty list of strings")
    nxt = obj["next_experiment"]
    if nxt != "ready_to_patch" and nxt not in MENU:
        raise ValidationError(f"next_experiment must be one of {list(MENU)} or ready_to_patch")
    return obj


def build_investigate_prompt(classification, results):
    from .experiments import MENU
    return ("Respond with ONLY a JSON object, no prose, with exactly these "
            "fields: ranked_hypotheses (non-empty list of short strings, most "
            "likely first), next_experiment (one of "
            f"{list(MENU)} or ready_to_patch).\n"
            f"symptom={classification.get('symptom')} reason={classification.get('reason')}\n"
            f"experiment_result={json.dumps(results[-1], default=str) if results else 'none'}")
