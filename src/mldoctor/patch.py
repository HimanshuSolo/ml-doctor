"""Propose + apply source patches. Edits use exact old/new string pairs.

Strict validation (pydantic-pending; stdlib for now). apply_patch requires
each `old` snippet to appear exactly once to avoid silent mis-patches.
"""
import json

from .diagnose import diagnose


class PatchError(Exception):
    pass


class ValidationError(Exception):
    pass


def parse_patch(text):
    from .diagnose import extract_json
    try:
        obj = json.loads(extract_json(text))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"not JSON: {exc}") from exc
    if type(obj) is not dict or set(obj) != {"path", "edits", "rationale"}:
        raise ValidationError("fields must be exactly [path, edits, rationale]")
    if type(obj["path"]) is not str or not obj["path"].strip():
        raise ValidationError("path must be a non-empty string")
    if type(obj["rationale"]) is not str or not obj["rationale"].strip():
        raise ValidationError("rationale must be a non-empty string")
    edits = obj["edits"]
    if type(edits) is not list or not edits:
        raise ValidationError("edits must be a non-empty list")
    for e in edits:
        if type(e) is not dict or set(e) != {"old", "new"}:
            raise ValidationError("each edit must be exactly {old, new}")
        if type(e["old"]) is not str or not e["old"]:
            raise ValidationError("edit.old must be a non-empty string")
        if type(e["new"]) is not str:
            raise ValidationError("edit.new must be a string")
    return obj


def apply_patch(source_text, patch):
    out = source_text
    for e in patch["edits"]:
        if out.count(e["old"]) != 1:
            raise PatchError(f"old snippet found {out.count(e['old'])}x, need 1x")
        out = out.replace(e["old"], e["new"], 1)
    return out


def propose_patch(diagnosis, source, client, hot_windows=None):
    # The patch model sees the merge-flagged windows (or the head of the
    # file): exact `old` snippets must come from visible text.
    visible = "\n---\n".join(text for _, _, text in (hot_windows or [])) or source
    prompt = ("Respond with ONLY a JSON object, no prose, with exactly these "
              "fields: path, edits (a list of {old, new} exact substrings of "
              "the SHOWN source; each old must appear exactly once), rationale.\n"
              f"symptom={diagnosis['symptom']} plan={diagnosis['fix_plan']}\nsource:\n{visible[:12000]}")
    return parse_patch(client.complete(prompt, purpose="patch"))


def diagnose_and_patch(classification, source, client):
    from .diagnose import diagnose_large
    diagnosis, hot_windows = diagnose_large(classification, source, client)
    patch = propose_patch(diagnosis, source, client, hot_windows=hot_windows)
    return diagnosis, patch, apply_patch(source, patch)
