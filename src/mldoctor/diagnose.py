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


# Chunked diagnosis for large files: the single-shot prompt only sees the
# first 4000 chars, so bugs later in a big pipeline are invisible to the
# model. Windows overlap so a bug on a boundary is fully seen by one window.
CHUNK_WINDOW = 3500
CHUNK_OVERLAP = 500
SINGLE_SHOT_LIMIT = 4000


def chunk_source(source, window=CHUNK_WINDOW, overlap=CHUNK_OVERLAP):
    """Split source into overlapping (index, start_char, text) windows."""
    if len(source) <= SINGLE_SHOT_LIMIT:
        return [(0, 0, source)]
    step = window - overlap
    out, start, i = [], 0, 0
    while start < len(source):
        out.append((i, start, source[start:start + window]))
        if start + window >= len(source):
            break
        start += step
        i += 1
    return out


def build_chunk_prompt(classification, index, n_windows, window_text):
    intro = ("Respond with ONLY a JSON object, no prose, with exactly these "
             "fields: window (int), suspects (non-empty list of short strings: "
             "concrete lines or patterns in THIS window that could cause the "
             "symptom; use 'none' as the single entry when clean).")
    ctx = ("symptom=%s reason=%s\nwindow %d/%d of source:\n%s"
           % (classification.get("symptom"), classification.get("reason"),
              index + 1, n_windows, window_text))
    return intro + "\n" + ctx


def build_merge_prompt(classification, findings, n_scanned, n_total):
    intro = ("Respond with ONLY a JSON object, no prose, with exactly these "
             "fields: symptom (one of healthy, non_reproducible, diverged, "
             "error), reason, culprit, fix_plan.")
    ctx = ("symptom=%s reason=%s\nper-window findings (scanned %d of %d windows):\n%s\n"
           "Merge into one diagnosis for the whole file; name the window "
           "number holding the culprit inside culprit."
           % (classification.get("symptom"), classification.get("reason"),
              n_scanned, n_total,
              "\n".join("- window %s: %s" % (f["window"], "; ".join(map(str, f["suspects"])))
                         for f in findings)))
    return intro + "\n" + ctx


def parse_chunk(text):
    try:
        obj = json.loads(extract_json(text))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"not JSON: {exc}") from exc
    if type(obj) is not dict or type(obj.get("window")) is not int:
        raise ValidationError("chunk finding must carry an int window")
    if type(obj.get("suspects")) is not list or not obj["suspects"]:
        raise ValidationError("chunk finding must carry a non-empty suspects list")
    return obj


def _remaining_calls(client):
    budget = getattr(client, "budget", None)
    if budget is None:
        return 1
    try:
        return max(0, budget.max_calls - budget.call_count)
    except Exception:
        return 1


def diagnose_large(classification, source, client):
    """Diagnose a possibly-large source. Small files take the original
    single-shot path (1 call). Large files are scanned window by window and
    merged (windows + 1 merge call), capped by the remaining call budget:
    with too little budget left, degrade honestly to the single-shot path.
    Returns (diagnosis, hot_windows) where hot_windows are the scanned
    window texts for the patch step."""
    windows = chunk_source(source)
    if len(windows) == 1:
        return diagnose(classification, source, client), windows
    room = _remaining_calls(client) - 1  # reserve the merge call
    if room < 1:
        return diagnose(classification, source, client), windows[:1]
    # Evenly spaced windows cover the whole file within budget.
    if len(windows) > room:
        idx = sorted({round(i * (len(windows) - 1) / (room - 1)) if room > 1 else 0
                      for i in range(room)})
        picked = [windows[i] for i in idx]
    else:
        picked = windows
    findings = []
    for index, start, text in picked:
        try:
            findings.append(parse_chunk(client.complete(
                build_chunk_prompt(classification, index, len(windows), text),
                purpose="diagnose_chunk")))
        except ValidationError:
            findings.append({"window": index, "suspects": ["unparseable window"]})
    diagnosis = parse_diagnosis(client.complete(
        build_merge_prompt(classification, findings, len(picked), len(windows)),
        purpose="diagnose"))
    return diagnosis, [(i, s, t) for i, s, t in picked]
