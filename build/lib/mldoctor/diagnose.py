"""Diagnose symptom from classification + source via LLM (mock by default).

Strict stdlib validation mirrors pydantic strict + extra=forbid (pydantic
install pending approval; see assumptions). No network on mock path.
"""
import json

SYMPTOMS = ("healthy", "non_reproducible", "diverged", "error")
_FIELDS = ("symptom", "reason", "culprit", "fix_plan")


class ValidationError(Exception):
    pass


def parse_diagnosis(text):
    try:
        obj = json.loads(text)
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
    return (f"symptom={classification.get('symptom')} "
            f"reason={classification.get('reason')}\n"
            f"source:\n{source[:4000]}")


def diagnose(classification, source, client):
    return parse_diagnosis(client.complete(build_prompt(classification, source),
                                           purpose="diagnose"))
