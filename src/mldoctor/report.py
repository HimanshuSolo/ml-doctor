"""Single self-contained HTML report for one finished run."""
import html
import os

NA = "Not applicable: no problem detected"


def _rel(path):
    if not path:
        return ""
    p = str(path)
    if not os.path.isabs(p):
        return p
    rel = os.path.relpath(p, os.getcwd())
    return rel if not rel.startswith("../..") else os.path.basename(p)


def _finite(v):
    return v is not None and v == v and abs(v) != float("inf")


def _exploded(curves):
    for c in curves:
        first = next((y for y in c if _finite(y)), None)
        for i, y in enumerate(c):
            if y is None or not _finite(y):
                return i
            if first is not None and abs(y) > max(1.0, abs(first)) * 10:
                return i
    return None


def _svg(ev, title):
    if not ev or not ev.get("loss_curves"):
        return f"<h3>{html.escape(title)}</h3><p>no data</p>"
    curves = ev["loss_curves"]
    flat = [y for c in curves for y in c if _finite(y)]
    mx, mn = (max(flat) if flat else 1), (min(flat) if flat else 0)
    W, H = 560, 160
    polys = []
    for i, c in enumerate(curves):
        pts = " ".join(f"{j / max(len(c) - 1, 1) * W:.1f},{H - (y - mn) / max(mx - mn, 1e-9) * H:.1f}"
                       for j, y in enumerate(c) if _finite(y))
        polys.append(f'<polyline fill="none" stroke="hsl({190 + i * 40},70%,45%)" points="{pts}"/>')
    boom = _exploded(curves)
    marker = ""
    if boom is not None:
        x = boom / max(max((len(c) for c in curves), default=1) - 1, 1) * W
        marker = (f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{H}" stroke="#c0392b" stroke-dasharray="4 3"/>'
                  f'<text x="{min(x + 6, W - 140):.1f}" y="16" fill="#c0392b" font-size="12">exploded at step {boom}</text>')
    rows = []
    for i, c in enumerate(curves):
        fin = [y for y in c if _finite(y)]
        peak = f"{max(fin):.4g}" if fin else "non-finite"
        final = f"{fin[-1]:.4g}" if fin and _finite(c[-1]) else "non-finite"
        rows.append(f"<tr><td>{i}</td><td>{peak}</td><td>{final}</td></tr>")
    table = ("<table><thead><tr><th>run</th><th>peak loss</th><th>final loss</th></tr></thead>"
             f"<tbody>{''.join(rows)}</tbody></table>")
    return (f"<h3>{html.escape(title)}</h3><svg width='{W}' height='{H}' "
            f"style='background:#f4f4f4'>{''.join(polys)}{marker}</svg>{table}")


def _hashes(ev, title):
    if not ev or not ev.get("hash_fingerprints"):
        return f"<h4>{html.escape(title)}</h4><p>no data</p>"
    rows = "<br>".join(f"run {i}: {' '.join(r)}" for i, r in enumerate(ev["hash_fingerprints"]))
    return (f"<h4>{html.escape(title)}</h4>"
            f"<p style='font-family:monospace;font-size:12px'>{rows}</p>")


def render_report(s):
    c = s.get("classification") or {}
    d = s.get("diagnosis")
    v = s.get("verification")
    ev = s.get("evidence") or {}
    healthy = c.get("symptom") == "healthy"
    mock = s.get("mock", True)
    mode = "MOCK" if mock else "LIVE"
    # Single source for both lines, so verification and verdict cannot disagree.
    if healthy:
        verdict, ver_text = "HEALTHY (no fix needed)", NA
    elif v:
        ok = bool(v.get("passed"))
        verdict = "PASS" if ok else "FAIL"
        k, seeds = v.get("k"), v.get("seeds") or []
        if v.get("mode") == "seeds" and seeds:
            detail = f"{k} seeds ({seeds[0]}-{seeds[-1]}) finite" if ok else f"{k} seeds ({seeds[0]}-{seeds[-1]}), not all finite"
        elif v.get("mode") == "seeds":
            detail = f"{k} seeds finite" if ok else f"{k} seeds, not all finite"
        else:
            detail = f"{k} runs identical" if ok else f"{k} runs, not identical"
        ver_text = f"{verdict} — {detail}: {v.get('reason') or ''}"
        if v.get("violations"):
            ver_text += f" (violations: {'; '.join(v['violations'])})"
    else:
        verdict = "PASS" if s.get("passed") else "FAIL"
        ver_text = "Not applicable: no verification ran"
    usage = (f"mock calls: {s.get('llm_calls', 0)}, simulated tokens: {s.get('tokens_used', 0)}" if mock
             else f"model calls: {s.get('llm_calls', 0)}, tokens used: {s.get('tokens_used', 0)}")
    hyp = NA if healthy else (f"{html.escape(d.get('culprit', ''))} — {html.escape(d.get('fix_plan', ''))}" if d else "no diagnosis")
    experiments = s.get("experiments")
    exp_text = NA if healthy else ("; ".join(str(e) for e in experiments) if experiments else "none (single-pass diagnosis)")
    diff_html = NA if healthy else f"<pre>{html.escape(s.get('diff') or 'no diff')}</pre>"
    after_html = f"<h3>Loss curves — after patch</h3><p>{NA}</p>" if healthy else _svg(ev.get("after"), "Loss curves — after patch")
    after_hashes = f"<p>{NA}</p>" if healthy else _hashes(ev.get("after"), "After patch")
    criterion = ""
    if c.get("symptom") == "diverged":
        criterion = "<p>Different seeds produce different hashes by design; the pass criterion is finite, sane loss.</p>"
    elif c.get("symptom") == "non_reproducible":
        criterion = "<p>Pass criterion: identical hashes across runs.</p>"
    patched = s.get("patched_path")
    patched_line = f"<p><b>Patched script:</b> {html.escape(_rel(patched))}</p>" if patched and not healthy else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>MLDoctor report</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}pre{{background:#111;color:#eee;padding:1rem;overflow:auto}}table{{border-collapse:collapse}}td,th{{border:1px solid #999;padding:2px 8px}}</style></head>
<body><h1>MLDoctor report</h1>
<p><b>Mode:</b> {mode} | <b>Script:</b> {html.escape(_rel(s.get('script')))}</p>{patched_line}
<p><b>Symptom:</b> {html.escape(str(c.get('symptom') or 'unknown'))} — {html.escape(str(c.get('reason') or ''))}</p>
{_svg(ev.get('before'), 'Loss curves — before')}
{after_html}
<h3>Parameter hash fingerprints</h3>{criterion}{_hashes(ev.get('before'), 'Before patch')}{after_hashes}
<h3>Hypotheses</h3><p>{hyp}</p>
<h3>Experiments run</h3><p>{html.escape(exp_text)}</p>
<h3>Diff</h3>{diff_html}
<h3>Verification</h3><p>{html.escape(ver_text)}</p>
<p><b>Verdict:</b> {verdict} | {usage}</p>
</body></html>"""
