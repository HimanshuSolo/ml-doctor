"""Single self-contained HTML report for one finished run."""
import html


def _svg(ev, title):
    if not ev or not ev.get("loss_curves"):
        return f"<h3>{html.escape(title)}</h3><p>no data</p>"
    curves = ev["loss_curves"]
    flat = [y for c in curves for y in c if y is not None and y == y and abs(y) != float("inf")]
    mx, mn = (max(flat) if flat else 1), (min(flat) if flat else 0)
    W, H = 560, 160
    polys = []
    for i, c in enumerate(curves):
        pts = " ".join(f"{j / max(len(c) - 1, 1) * W:.1f},{H - (y - mn) / max(mx - mn, 1e-9) * H:.1f}"
                       for j, y in enumerate(c) if y is not None)
        polys.append(f'<polyline fill="none" stroke="hsl({i * 70},70%,35%)" points="{pts}"/>')
    hashes = "<br>".join(f"run {i}: {' '.join(r)}" for i, r in enumerate(ev.get("hash_fingerprints", [])))
    return (f"<h3>{html.escape(title)}</h3><svg width='{W}' height='{H}' "
            f"style='background:#f4f4f4'>{''.join(polys)}</svg>"
            f"<p style='font-family:monospace;font-size:12px'>{hashes}</p>")


def render_report(s):
    c = s.get("classification") or {}
    d = s.get("diagnosis") or {}
    v = s.get("verification") or {}
    ev = s.get("evidence") or {}
    mode = "MOCK" if s.get("mock", True) else "LIVE"
    hyp = (f"<p>{html.escape(d.get('culprit', '—'))} — {html.escape(d.get('fix_plan', ''))}</p>"
           if d else "<p>—</p>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>MLDoctor report</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}pre{{background:#111;color:#eee;padding:1rem;overflow:auto}}</style></head>
<body><h1>MLDoctor report</h1>
<p><b>Mode:</b> {mode} (live path UNVERIFIED against Baseten) | <b>Script:</b> {html.escape(str(s.get('script', '')))}</p>
<p><b>Symptom:</b> {html.escape(str(c.get('symptom', '—')))} — {html.escape(str(c.get('reason', '')))}</p>
{_svg(ev.get('before'), 'Loss curves — before')}
{_svg(ev.get('after'), 'Loss curves — after patch')}
<h3>Hypotheses</h3>{hyp}
<h3>Experiments run</h3><p>none</p>
<h3>Diff</h3><pre>{html.escape(s.get('diff') or '—')}</pre>
<h3>Verification</h3><p>{'PASS' if v.get('passed') else 'FAIL'} — {html.escape(str(v.get('reason', '—')))}
(k={v.get('k')}, mode={html.escape(str(v.get('mode', '')))}, seeds={v.get('seeds')})</p>
<p><b>Verdict:</b> {'PASS' if s.get('passed') else 'FAIL'} | model calls: {s.get('llm_calls', 0)} |
tokens used: {s.get('tokens_used', 0)}</p>
</body></html>"""
