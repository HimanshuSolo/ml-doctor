"use client";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { initialState, reduce } from "@/lib/reducer";
import type { ServerState } from "@/lib/events";
import { DiffView, HashCells, LossChart, RunGrid } from "@/components/charts";
import { EventLog, Hud, Odometer, stepIndex } from "@/components/hud";

const TOKEN_KEY = "mldoctor-token";
function getToken(): string {
  if (typeof window === "undefined") return "";
  const fromUrl = new URLSearchParams(window.location.search).get("token");
  if (fromUrl) { sessionStorage.setItem(TOKEN_KEY, fromUrl); history.replaceState(null, "", window.location.pathname); return fromUrl; }
  return sessionStorage.getItem(TOKEN_KEY) ?? "";
}
function errorForStatus(status: number, text: string): string {
  if (status === 401) return "Token missing or invalid. Open the dashboard from the URL printed by `mldoctor serve`.";
  if (status === 409) return "A run is already active. Wait for it to finish.";
  if (status === 403) return "Live not configured on the server (MLDOCTOR_BASE_URL, MLDOCTOR_MODEL, MLDOCTOR_API_KEY).";
  if (status === 400) return `Script not allowed: ${text || "must be a .py file inside the allowed directory."}`;
  return `Server error ${status}: ${text}`;
}

export default function Page() {
  const [s, dispatch] = useReducer(reduce, initialState);
  const tokenRef = useRef("");
  const [script, setScript] = useState("fixtures/repro.py");
  const [k, setK] = useState(2);
  const [verifyK, setVerifyK] = useState("");
  const [live, setLive] = useState(false);
  const [pacing, setPacing] = useState(false);
  const [conn, setConn] = useState<"connecting" | "open" | "error">("connecting");
  const [beforeAfter, setBeforeAfter] = useState<"before" | "after">("before");
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const t = getToken(); tokenRef.current = t;
    if (!t) { dispatch({ kind: "run_error", error: "Token missing. Open the dashboard from the URL printed by `mldoctor serve` (it carries ?token=)." }); return; }
    fetch("/api/state", { headers: { "X-MLDoctor-Token": t } })
      .then(async (r) => { if (!r.ok) throw new Error(errorForStatus(r.status, await r.text())); dispatch({ kind: "server_state", state: (await r.json()) as ServerState }); })
      .catch((e: Error) => dispatch({ kind: "server_unreachable", error: `Server unreachable: ${e.message}` }));
    const es = new EventSource(`/api/events?token=${encodeURIComponent(t)}`);
    es.onopen = () => setConn("open");
    es.onerror = () => setConn("error");
    es.onmessage = (m) => { try { dispatch({ kind: "event", event: JSON.parse(m.data) }); } catch { /* heartbeat / non-JSON */ } };
    return () => es.close();
  }, []);

  // After a run completes, refresh summary-derived budget numbers from the server.
  useEffect(() => {
    if (s.phase !== "done" || !tokenRef.current) return;
    fetch("/api/state", { headers: { "X-MLDoctor-Token": tokenRef.current } })
      .then((r) => (r.ok ? r.json() : null)).then((j) => { if (j) dispatch({ kind: "server_state", state: j as ServerState }); }).catch(() => {});
  }, [s.phase]);

  async function run() {
    const token = tokenRef.current;
    if (!token) { dispatch({ kind: "run_error", error: "Token missing. Open the dashboard from the URL printed by `mldoctor serve`." }); return; }
    if (live && !window.confirm(`Enable LIVE model calls? Per-run call cap: ${s.callCap ?? 8}.`)) return;
    dispatch({ kind: "run_started", script });
    try {
      const r = await fetch("/api/run", { method: "POST", headers: { "X-MLDoctor-Token": token, "Content-Type": "application/json" },
        body: JSON.stringify({ script, k, verify_k: verifyK ? Number(verifyK) : null, live, demo_pacing: pacing && !live }) });
      if (!r.ok) dispatch({ kind: "run_error", error: errorForStatus(r.status, await r.text()) });
      else fetch("/api/state", { headers: { "X-MLDoctor-Token": token } })
        .then((x) => (x.ok ? x.json() : null))
        .then((j) => { if (j) dispatch({ kind: "server_state", state: j as ServerState }); })
        .catch(() => {}); // server-reported demo_pacing / mode, shown during the run
    } catch (e) { dispatch({ kind: "server_unreachable", error: `Server unreachable: ${e instanceof Error ? e.message : String(e)}` }); }
  }

  const hypotheses = useMemo(() => {
    const cards = [
      { id: "classification", title: `Classification: ${s.symptom ?? "—"}`, body: s.reason ?? "Waiting for baseline_completed from the server.", rank: s.diagnosis ? 1 : 0 },
      ...(s.diagnosis ? [{ id: "diagnosis", title: `Diagnosis: ${s.diagnosis.culprit}`, body: `${s.diagnosis.fix_plan} (${s.diagnosis.reason})`, rank: 0 }] : []),
      ...(s.patch ? [{ id: "patch", title: "Patch rationale", body: s.patch.rationale, rank: 2 }] : []),
    ];
    return cards.sort((a, b) => a.rank - b.rank);
  }, [s.symptom, s.reason, s.diagnosis, s.patch]);
  const evidence = beforeAfter === "before" ? s.evidenceBefore : s.evidenceAfter;
  // Sections are never hidden waiting for motion: content is visible in the
  // prerendered HTML; the reveal is only a small slide once scrolled into view.
  const section = { initial: reduceMotion ? false : { opacity: 1, y: 10 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true } } as const;

  return (
    <div className="min-h-screen">
      <Hud s={s} />
      <main className="mx-auto max-w-6xl space-y-10 px-4 py-6">
        {s.error && <div role="alert" className="rounded border border-redx bg-redx/10 p-3 text-sm text-redx">{s.error}</div>}
        {conn === "error" && !s.error && <div role="alert" className="rounded border border-amberx bg-amberx/10 p-3 text-sm text-amberx">Event stream disconnected. Data shown is the last server-reported state.</div>}

        <motion.section {...section} aria-labelledby="h-hero" className="space-y-4">
          <h1 id="h-hero" className="text-3xl font-bold">Run launcher</h1>
          <p className="max-w-2xl text-dim">Reproduce, investigate, patch and verify a broken training script. Every number below comes from a server event — nothing is simulated.</p>
          <form className="grid gap-3 rounded border border-line bg-panel p-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); void run(); }}>
            <label className="block text-sm">Script path (inside allowed dir)
              <input value={script} onChange={(e) => setScript(e.target.value)} className="mt-1 w-full rounded border border-line bg-panel2 p-2 font-mono text-sm" /></label>
            <label className="block text-sm">Baseline runs (-k)
              <input type="number" min={1} max={10} value={k} onChange={(e) => setK(Number(e.target.value))} className="mt-1 w-full rounded border border-line bg-panel2 p-2 font-mono text-sm" /></label>
            <label className="block text-sm">Verify runs (empty = spec: 10 non-reproducible / 5 diverged seeds)
              <input type="number" min={1} max={20} value={verifyK} onChange={(e) => setVerifyK(e.target.value)} className="mt-1 w-full rounded border border-line bg-panel2 p-2 font-mono text-sm" /></label>
            <div className="flex flex-wrap items-end gap-4 pb-1 text-sm">
              <label><input type="checkbox" checked={live} disabled={!s.liveConfigured} onChange={(e) => setLive(e.target.checked)} /> Live model{!s.liveConfigured ? " (not configured)" : ""}</label>
              <label><input type="checkbox" checked={pacing} disabled={live} onChange={(e) => setPacing(e.target.checked)} /> Demo pacing (MOCK only)</label>
            </div>
            <button type="submit" disabled={s.phase === "running"} className="rounded bg-bluex px-4 py-2 font-semibold text-black disabled:opacity-50">{s.phase === "running" ? "Running…" : "Run pipeline"}</button>
            <p className="self-center font-mono text-xs text-dim" role="status">{s.phase === "idle" ? "idle — no run yet" : s.phase} · step: {stepIndex(s) >= 0 ? ["Reproduce", "Classify", "Investigate", "Patch", "Verify"][stepIndex(s)] : "—"}</p>
          </form>
          <EventLog s={s} />
        </motion.section>

        <motion.section {...section} aria-labelledby="h-repro" className="space-y-3">
          <h2 id="h-repro" className="text-2xl font-bold">Reproduce</h2>
          <div className="flex gap-2" role="group" aria-label="Evidence toggle">
            {(["before", "after"] as const).map((v) => <button key={v} type="button" aria-pressed={beforeAfter === v} onClick={() => setBeforeAfter(v)} className={`rounded border px-3 py-1 text-sm ${beforeAfter === v ? "border-bluex text-bluex" : "border-line text-dim"}`}>{v === "before" ? "Before patch" : "After patch"}</button>)}
          </div>
          <LossChart evidence={evidence} title={beforeAfter === "before" ? "Baseline loss curves" : "Patched loss curves"} />
          <HashCells evidence={evidence} title={beforeAfter === "before" ? "Baseline hash fingerprints" : "Patched hash fingerprints"} />
        </motion.section>

        <motion.section {...section} aria-labelledby="h-inv" className="space-y-3">
          <h2 id="h-inv" className="text-2xl font-bold">Investigate</h2>
          {hypotheses.length === 1 && !s.diagnosis && !s.symptom ? <p className="text-dim text-sm">No hypothesis yet — the diagnosis card appears only when the server sends it.</p> : (
            <div className="grid gap-3 sm:grid-cols-2">
              {hypotheses.map((c) => (
                <motion.article key={c.id} layout={!reduceMotion} className="rounded border border-line bg-panel p-4">
                  <h3 className="font-semibold">{c.title}</h3><p className="mt-1 text-sm text-dim">{c.body}</p>
                </motion.article>
              ))}
            </div>
          )}
        </motion.section>

        <motion.section {...section} aria-labelledby="h-patch" className="space-y-3">
          <h2 id="h-patch" className="text-2xl font-bold">Patch</h2>
          {s.patchedPath && <p className="font-mono text-xs text-dim">Patched file: {s.patchedPath}</p>}
          <DiffView diff={s.diff} violations={s.violations} />
        </motion.section>

        <motion.section {...section} aria-labelledby="h-verify" className="space-y-4">
          <h2 id="h-verify" className="text-2xl font-bold">Verify</h2>
          <Odometer value={s.nDone} total={s.nTotal} />
          <RunGrid nDone={s.nDone} nTotal={s.nTotal} nFailed={s.nFailed} runs={s.runs} verdict={s.verdict} />
          <div aria-live="polite" className={`inline-block rounded border-4 px-6 py-3 text-3xl font-black tracking-widest ${s.verdict === "PASS" ? "border-greenx text-greenx" : s.verdict === "FAIL" ? "border-redx text-redx" : "border-line text-dim"}`}>
            {s.verdict ?? "NO VERDICT YET"}
          </div>
          {s.verdictReason && <p className="text-sm text-dim">{s.verdictReason}</p>}
          {s.verdict === "FAIL" && <p className="text-sm">This patch was rejected or did not verify. That is a real result, shown with the same weight as a pass.</p>}
        </motion.section>

        <motion.section {...section} aria-labelledby="h-report" className="space-y-3">
          <h2 id="h-report" className="text-2xl font-bold">Report</h2>
          {s.phase === "done" ? <button type="button" className="rounded bg-tealx px-4 py-2 font-semibold text-black" onClick={async () => { const r = await fetch("/api/report", { headers: { "X-MLDoctor-Token": tokenRef.current } }); if (!r.ok) return; const url = URL.createObjectURL(await r.blob()); const a = document.createElement("a"); a.href = url; a.download = "mldoctor-report.html"; a.click(); URL.revokeObjectURL(url); }}>Download HTML report</button>
            : <p className="text-dim text-sm">Report download appears after a run finishes.</p>}
          <h3 className="font-semibold">Run history (this browser session)</h3>
          {s.history.length === 0 ? <p className="text-dim text-sm">No completed runs yet.</p>
            : <ul className="space-y-1 font-mono text-sm">{s.history.map((h, i) => <li key={i} className="rounded border border-line bg-panel px-3 py-2">{new Date(h.at * 1000).toLocaleTimeString()} · {h.script} · {h.verdict} ({h.passed ? "passed" : "not passed"})</li>)}</ul>}
        </motion.section>
      </main>
      {/* Decorative only: faint grid backdrop, carries no data. */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 opacity-[0.12]" style={{ backgroundImage: "linear-gradient(#1d3355 1px, transparent 1px), linear-gradient(90deg, #1d3355 1px, transparent 1px)", backgroundSize: "44px 44px" }} />
    </div>
  );
}
