"use client";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { initialState, reduce } from "@/lib/reducer";
import type { ServerState } from "@/lib/events";
import { API_BASE, apiUrl } from "@/lib/api";
import { HashCells, LossChart, RunGrid } from "@/components/charts";
import { EventLog, Hud, Odometer, stepIndex } from "@/components/hud";
import { CubesGate, RibbonsGate, TrajectoryGate } from "@/components/three/Gated3D";
import InvestigationPanel from "@/components/InvestigationPanel";
import CodeIntake from "@/components/CodeIntake";
import ProofPanel from "@/components/ProofPanel";
import PersistentCanvas from "@/components/chrome/PersistentCanvas";
import Cursor from "@/components/chrome/Cursor";
import Boot from "@/components/chrome/Boot";
import Ticker from "@/components/chrome/Ticker";
import SmoothScroll from "@/components/chrome/SmoothScroll";
import VerdictMoment from "@/components/chrome/VerdictMoment";
import PipelineTube from "@/components/chrome/PipelineTube";
import PatchScanner from "@/components/PatchScanner";
import ExperimentGraph from "@/components/ExperimentGraph";
import Reveal from "@/components/chrome/Reveal";
import Rail from "@/components/chrome/Rail";

const DEMO_SCRIPTS = ["fixtures/repro.py", "fixtures/diverge.py", "fixtures/healthy.py"];
const HISTORY_KEY = "mldoctor-history";

const TOKEN_KEY = "mldoctor-token";
function hasToken(): boolean {
  if (typeof window === "undefined") return true;
  return new URLSearchParams(window.location.search).has("token") || Boolean(sessionStorage.getItem(TOKEN_KEY));
}
function getToken(): string {
  if (typeof window === "undefined") return "";
  const fromUrl = new URLSearchParams(window.location.search).get("token");
  if (fromUrl) { sessionStorage.setItem(TOKEN_KEY, fromUrl); history.replaceState(null, "", window.location.pathname); return fromUrl; }
  return sessionStorage.getItem(TOKEN_KEY) ?? "";
}
function errorForStatus(status: number, text: string): string {
  if (status === 401) return "Token missing or invalid. Paste the ?token= printed by `mldoctor serve` into the token box.";
  if (status === 409) return "A run is already active. Wait for it to finish.";
  if (status === 403) return "Live not configured on the server (MLDOCTOR_BASE_URL, MLDOCTOR_MODEL, MLDOCTOR_API_KEY).";
  if (status === 400) return `Script not allowed: ${text || "must be a .py file inside the allowed directory."}`;
  return `Server error ${status}: ${text}`;
}

export default function Page() {
  const [s, dispatch] = useReducer(reduce, initialState);
  const tokenRef = useRef("");
  const [script, setScript] = useState("fixtures/repro.py");
  const [fixtures, setFixtures] = useState<string[]>([]);
  const [k, setK] = useState(2);
  const [verifyK, setVerifyK] = useState("");
  const [live, setLive] = useState(false);
  const [pacing, setPacing] = useState(false);
  const [investigate, setInvestigate] = useState(false);
  const [vision, setVision] = useState(false);
  const [conn, setConn] = useState<"connecting" | "open" | "error">("connecting");
  const [needToken, setNeedToken] = useState(false);
  const [tokenDraft, setTokenDraft] = useState("");
  const [beforeAfter, setBeforeAfter] = useState<"before" | "after">("before");
  const reduceMotion = useReducedMotion();

  // Ref of the current SSE connection so a pasted token re-connects cleanly.
  const esRef = useRef<EventSource | null>(null);
  function connect(t: string) {
    tokenRef.current = t;
    setConn("connecting");
    dispatch({ kind: "clear_error" });
    fetch(apiUrl("/api/state"), { headers: { "X-MLDoctor-Token": t } })
      .then(async (r) => { if (!r.ok) throw new Error(errorForStatus(r.status, await r.text())); dispatch({ kind: "server_state", state: (await r.json()) as ServerState }); })
      .catch((e: Error) => dispatch({ kind: "server_unreachable", error: `Server unreachable at ${API_BASE}: ${e.message}. Is the backend running there (two-process? with MLDOCTOR_DEV_CORS=1)?` }));
    fetch(apiUrl("/api/fixtures"), { headers: { "X-MLDoctor-Token": t } })
      .then((r) => (r.ok ? r.json() : null)).then((j) => { if (j?.fixtures) setFixtures(j.fixtures as string[]); }).catch(() => {});
    esRef.current?.close();
    const es = new EventSource(apiUrl(`/api/events?token=${encodeURIComponent(t)}`));
    esRef.current = es;
    es.onopen = () => setConn("open");
    es.onerror = () => setConn("error");
    es.onmessage = (m) => { try { dispatch({ kind: "event", event: JSON.parse(m.data) }); } catch { /* heartbeat / non-JSON */ } };
  }

  useEffect(() => {
    const t = getToken();
    // One-time mount check + subscription to external systems (fetch + EventSource).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!t) { setNeedToken(true); dispatch({ kind: "run_error", error: "Token missing. Paste the ?token= printed by `mldoctor serve`." }); return; }
    connect(t);
    return () => esRef.current?.close();
  }, []);

  // After a run completes, refresh summary-derived budget numbers from the server.
  useEffect(() => {
    if (s.phase !== "done" || !tokenRef.current) return;
    fetch(apiUrl("/api/state"), { headers: { "X-MLDoctor-Token": tokenRef.current } })
      .then((r) => (r.ok ? r.json() : null)).then((j) => { if (j) dispatch({ kind: "server_state", state: j as ServerState }); }).catch(() => {});
  }, [s.phase]);

  const [demoQueue, setDemoQueue] = useState<string[]>([]);
  async function runScript(target: string) {
    const token = tokenRef.current;
    if (!token) { setNeedToken(true); dispatch({ kind: "run_error", error: "Token missing. Paste the ?token= printed by `mldoctor serve`." }); return; }
    setScript(target);
    dispatch({ kind: "run_started", script: target });
    try {
      const r = await fetch(apiUrl("/api/run"), { method: "POST", headers: { "X-MLDoctor-Token": token, "Content-Type": "application/json" },
        body: JSON.stringify({ script: target, k, verify_k: verifyK ? Number(verifyK) : null, live, demo_pacing: pacing && !live, investigate, vision }) });
      if (!r.ok) { setDemoQueue([]); dispatch({ kind: "run_error", error: errorForStatus(r.status, await r.text()) }); }
      else fetch(apiUrl("/api/state"), { headers: { "X-MLDoctor-Token": token } })
        .then((x) => (x.ok ? x.json() : null))
        .then((j) => { if (j) dispatch({ kind: "server_state", state: j as ServerState }); })
        .catch(() => {}); // server-reported demo_pacing / mode, shown during the run
    } catch (e) { setDemoQueue([]); dispatch({ kind: "server_unreachable", error: `Server unreachable: ${e instanceof Error ? e.message : String(e)}` }); }
  }
  async function run() {
    if (live && !window.confirm(`Enable LIVE model calls? Per-run call cap: ${s.callCap ?? 8}.`)) return;
    setDemoQueue([]);
    await runScript(script);
  }
  // One-click demo: runs repro → diverge → healthy through the real API, in
  // order. Each leg is a genuine POST /api/run; the next starts only after the
  // server completes the previous one (phase flips to done/failed).
  function playDemo() {
    if (s.phase === "running") return;
    setDemoQueue(DEMO_SCRIPTS.slice(1));
    void runScript(DEMO_SCRIPTS[0]);
  }
  useEffect(() => {
    if (demoQueue.length === 0) return;
    if (s.phase !== "done" && s.phase !== "failed") return;
    const [next, ...rest] = demoQueue;
    // Chained-demo advance: fires only on a phase transition to done/failed
    // with a non-empty queue (early return above), then waits 600ms.
    const t = setTimeout(() => { setDemoQueue(rest); void runScript(next); }, 600);
    return () => clearTimeout(t);
    // runScript reads live toggles via closure; queue advance keys only on phase.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.phase, demoQueue]);
  // Persistent run history: hydrate once from localStorage, save on change.
  // Only completed entries the server reported via pipeline_completed.
  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      if (raw) dispatch({ kind: "hydrate_history", history: JSON.parse(raw) });
    } catch { /* corrupted storage: start empty, honestly */ }
  }, []);
  useEffect(() => {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(s.history.slice(-20))); } catch { /* storage full/blocked */ }
  }, [s.history]);

  const hypotheses = useMemo(() => {
    const cards = [
      { id: "classification", title: `Classification: ${s.symptom ?? "—"}`, body: s.reason ?? "Waiting for baseline_completed from the server.", rank: s.diagnosis ? 1 : 0 },
      ...(s.diagnosis ? [{ id: "diagnosis", title: `Diagnosis: ${s.diagnosis.culprit}`, body: `${s.diagnosis.fix_plan} (${s.diagnosis.reason})`, rank: 0 }] : []),
      ...(s.patch ? [{ id: "patch", title: "Patch rationale", body: s.patch.rationale, rank: 2 }] : []),
    ];
    return cards.sort((a, b) => a.rank - b.rank);
  }, [s.symptom, s.reason, s.diagnosis, s.patch]);
  const evidence = beforeAfter === "before" ? s.evidenceBefore : s.evidenceAfter;
  // Sections fade, rise and settle as they scroll into view (once each).
  const section = { initial: reduceMotion ? false : { opacity: 0, y: 40 }, whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-70px" }, transition: { duration: 0.75, ease: [0.22, 1, 0.36, 1] as const } } as const;
  const heading = (id: string, text: string) => (
    <div className="space-y-2">
      <h2 id={id} className="text-2xl font-bold">{text}</h2>
      <motion.span aria-hidden="true" className="block h-[3px] w-14 origin-left rounded bg-tealx"
        initial={reduceMotion ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }}
        viewport={{ once: true, margin: "-70px" }} transition={{ duration: 0.6, delay: 0.15, ease: [0.22, 1, 0.36, 1] }} />
    </div>
  );

  return (
    <div className="grain min-h-screen">
      <Boot /><Cursor /><PersistentCanvas running={s.phase === "running"} /><VerdictMoment s={s} /><SmoothScroll activeStep={stepIndex(s)} />
      <Hud s={s} conn={conn} /><Ticker s={s} />
      <main className="mx-auto max-w-6xl space-y-10 px-4 py-6">
        {s.error && <div role="alert" className="rounded border border-redx bg-redx/10 p-3 text-sm text-redx">{s.error}</div>}
        {needToken && (
          <form className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-panel p-3 text-sm" onSubmit={(e) => { e.preventDefault(); const t = tokenDraft.trim(); if (!t) return; sessionStorage.setItem("mldoctor-token", t); setNeedToken(false); setTokenDraft(""); connect(t); }}>
            <label htmlFor="token-input">Paste token from the server terminal:
              <input id="token-input" value={tokenDraft} onChange={(e) => setTokenDraft(e.target.value)} placeholder="token…" autoComplete="off" className="ml-2 rounded border border-line bg-panel2 p-2 font-mono text-sm" /></label>
            <button type="submit" className="rounded-md px-3 py-2 font-semibold transition-opacity hover:opacity-90" style={{ background: "var(--accent)", color: "var(--panel)" }}>Connect</button>
          </form>
        )}
        {conn === "error" && !s.error && <div role="alert" className="rounded border border-amberx bg-amberx/10 p-3 text-sm text-amberx">Event stream disconnected. Data shown is the last server-reported state.</div>}

        <motion.section {...section} aria-labelledby="h-hero" data-chapter-theme="dark" className="chapter-dark relative -mx-4 space-y-5 overflow-hidden px-4 pb-8 pt-8">
          <div className="relative">
          <p className="label">MLDoctor · reproducible-training debugger</p>
          <h1 id="h-hero" className="display-huge max-w-5xl">
            {"Debug the run. Prove the fix.".split(" ").map((w, i) => (
              <motion.span key={i} className="mr-[0.28em] inline-block"
                initial={reduceMotion ? false : { opacity: 0, y: 22, clipPath: "inset(0 0 100% 0)" }}
                animate={{ opacity: 1, y: 0, clipPath: "inset(0 0 0% 0)" }}
                transition={{ duration: 0.7, delay: 0.08 + i * 0.07, ease: [0.22, 1, 0.36, 1] }}>{w}</motion.span>
            ))}
          </h1>
          <motion.p className="max-w-2xl text-dim"
            initial={reduceMotion ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.55, ease: [0.22, 1, 0.36, 1] }}>Reproduce, investigate, patch and verify a broken training script. Every number below comes from a server event — nothing is simulated.</motion.p>
          <Reveal delay={0.08}>
          <form className="grid gap-3 rounded-lg border border-line bg-panel p-5 shadow-[0_18px_45px_-28px_rgba(24,36,32,0.45)] sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); void run(); }}>
            <div className="sm:col-span-2">
              <CodeIntake script={script} setScript={setScript} fixtures={fixtures}
                getToken={() => tokenRef.current}
                onError={(error) => dispatch({ kind: "run_error", error })}
                disabled={s.phase === "running"} />
            </div>
            <label className="block text-sm">Baseline runs (-k)
              <input type="number" min={1} max={10} value={k} onChange={(e) => setK(Number(e.target.value))} className="mt-1 w-full rounded border border-line bg-panel2 p-2 font-mono text-sm" /></label>
            <label className="block text-sm">Verify runs (empty = spec: 10 non-reproducible / 5 diverged seeds)
              <input type="number" min={1} max={20} value={verifyK} onChange={(e) => setVerifyK(e.target.value)} className="mt-1 w-full rounded border border-line bg-panel2 p-2 font-mono text-sm" /></label>
            <div className="flex flex-wrap items-end gap-4 pb-1 text-sm">
              <label><input type="checkbox" checked={live} disabled={!s.liveConfigured} onChange={(e) => setLive(e.target.checked)} /> Live model{!s.liveConfigured ? " (not configured)" : ""}</label>
              <label><input type="checkbox" checked={pacing} disabled={live} onChange={(e) => setPacing(e.target.checked)} /> Demo pacing (MOCK only)</label>
              <label><input type="checkbox" checked={investigate} onChange={(e) => setInvestigate(e.target.checked)} /> Investigate (experiment menu, max 3)</label>
              <label><input type="checkbox" checked={vision} onChange={(e) => setVision(e.target.checked)} /> Vision (loss-curve image, opt-in)</label>
            </div>
            <motion.button whileHover={reduceMotion ? undefined : { scale: 1.02 }} whileTap={reduceMotion ? undefined : { scale: 0.98 }} type="submit" disabled={s.phase === "running"} className="magnetic rounded-full px-8 py-4 text-base font-semibold shadow-[0_0_36px_rgba(47,91,255,0.45)] transition-opacity duration-150 hover:opacity-90 disabled:opacity-50" style={{ background: "#2F5BFF", color: "#fff" }}>{s.phase === "running" ? "Running…" : "Run pipeline"}</motion.button>
            <div className="flex flex-col gap-1">
              <button type="button" onClick={playDemo} disabled={s.phase === "running"} className="rounded-md border border-tealx px-6 py-2 text-sm font-semibold text-tealx transition-colors duration-150 hover:bg-tealx/10 disabled:opacity-50">
                {demoQueue.length > 0 ? `Playing demo… ${DEMO_SCRIPTS.length - demoQueue.length}/${DEMO_SCRIPTS.length}` : "▶ Play full demo (repro → diverge → healthy)"}</button>
              <p className="font-mono text-xs text-dim" role="status">{s.phase === "idle" ? "idle — no run yet" : s.phase}{demoQueue.length > 0 ? ` · demo queue: ${demoQueue.join(", ")}` : ""} · step: {stepIndex(s) >= 0 ? ["Reproduce", "Classify", "Investigate", "Patch", "Verify"][stepIndex(s)] : "—"}</p>
            </div>
          </form>
          </Reveal>
          </div>
          <Reveal delay={0.05}><Rail s={s} /></Reveal>
          <Reveal delay={0.12}><EventLog s={s} /></Reveal>
        </motion.section>
        <section id="chapter-pipeline" aria-labelledby="h-pipe" data-chapter-theme="dark" className="chapter-dark -mx-4 rounded-3xl px-4 py-10" data-reveal>
          <p className="label">02 · The Pipeline</p>
          <h2 id="h-pipe" className="mt-2 text-4xl font-bold tracking-tight sm:text-5xl">Five stations. <span className="font-serif-accent text-[#6f8cff]">One truth.</span></h2>
          <PipelineTube s={s} />
        </section>

        <motion.section {...section} id="chapter-repro" aria-labelledby="h-repro" data-chapter-theme="light" className="chapter-light -mx-4 space-y-3 rounded-3xl px-4 py-8" data-reveal>
          {heading("h-repro", "Reproduce")}
          <div className="flex gap-2" role="group" aria-label="Evidence toggle">
            {(["before", "after"] as const).map((v) => <button key={v} type="button" aria-pressed={beforeAfter === v} onClick={() => setBeforeAfter(v)} className={`rounded border px-3 py-1 text-sm ${beforeAfter === v ? "border-bluex text-bluex" : "border-line text-dim"}`}>{v === "before" ? "Before patch" : "After patch"}</button>)}
          </div>
          <Reveal><LossChart evidence={evidence} title={beforeAfter === "before" ? "Baseline loss curves" : "Patched loss curves"} /></Reveal>
          <Reveal delay={0.08}><HashCells evidence={evidence} title={beforeAfter === "before" ? "Baseline hash fingerprints" : "Patched hash fingerprints"} /></Reveal>
          <Reveal delay={0.05}><h3 className="label">Loss ribbons · 3D</h3></Reveal>
          <Reveal delay={0.1}><RibbonsGate evidence={evidence} /></Reveal>
          <Reveal delay={0.05}><h3 className="label">Trajectory fan · 3D <span className="font-normal normal-case">(random 3D projection of parameters; axes have no meaning)</span></h3></Reveal>
          <Reveal delay={0.1}><TrajectoryGate evidence={evidence} /></Reveal>
        </motion.section>

        <motion.section {...section} id="chapter-investigate" aria-labelledby="h-inv" data-chapter-theme="dark" className="chapter-dark -mx-4 space-y-3 rounded-3xl px-4 py-8" data-reveal>
          {heading("h-inv", "Investigate")}
          <Reveal><InvestigationPanel s={s} /></Reveal>
          <Reveal delay={0.08}><ExperimentGraph s={s} /></Reveal>
          {hypotheses.length === 1 && !s.diagnosis && !s.symptom ? <p className="text-dim text-sm">No hypothesis yet — the diagnosis card appears only when the server sends it.</p> : (
            <div className="grid gap-3 sm:grid-cols-2">
              {hypotheses.map((c, ci) => (
                <motion.article key={c.id} layout={!reduceMotion}
                  initial={reduceMotion ? false : { opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-40px" }} transition={{ duration: 0.6, delay: ci * 0.09, ease: [0.22, 1, 0.36, 1] }}
                  className="rounded-lg border border-line bg-panel p-4">
                  <h3 className="font-semibold">{c.title}</h3><p className="mt-1 text-sm text-dim">{c.body}</p>
                </motion.article>
              ))}
            </div>
          )}
        </motion.section>

        <motion.section {...section} id="chapter-patch" aria-labelledby="h-patch" data-chapter-theme="light" className="chapter-light -mx-4 space-y-3 rounded-3xl px-4 py-8" data-reveal>
          {heading("h-patch", "Patch")}
          {s.patchedPath && <p className="font-mono text-xs text-dim">Patched file: {s.patchedPath}</p>}
          <Reveal><PatchScanner s={s} /></Reveal>
        </motion.section>

        <motion.section {...section} id="chapter-verify" aria-labelledby="h-verify" data-chapter-theme="dark" className="chapter-dark -mx-4 space-y-4 rounded-3xl px-4 py-8" data-reveal>
          {heading("h-verify", "Verify")}
          <Reveal><Odometer value={s.nDone} total={s.nTotal} /></Reveal>
          <Reveal delay={0.08}><RunGrid nDone={s.nDone} nTotal={s.nTotal} nFailed={s.nFailed} runs={s.runs} verdict={s.verdict} /></Reveal>
          <Reveal delay={0.05}><h3 className="label">Run cubes · 3D</h3></Reveal>
          <Reveal delay={0.1}><CubesGate runs={s.runs} verdict={s.verdict} /></Reveal>
          <div aria-live="polite" className={`inline-block rounded border-4 px-6 py-3 text-3xl font-black tracking-widest ${s.verdict === "PASS" ? "border-greenx text-greenx" : s.verdict === "FAIL" ? "border-redx text-redx" : "border-line text-dim"}`}>
            {s.verdict ?? "NO VERDICT YET"}
          </div>
          {s.verdictReason && <p className="text-sm text-dim">{s.verdictReason}</p>}
          {s.verdict === "FAIL" && <p className="text-sm">This patch was rejected or did not verify. That is a real result, shown with the same weight as a pass.</p>}
          {s.verdict !== null && (
            <div className="space-y-2">
              <h3 className="label">3D result chart — {s.verdict} (from real telemetry only)</h3>
              <TrajectoryGate evidence={s.evidenceAfter ?? s.evidenceBefore} />
              <RibbonsGate evidence={s.evidenceAfter ?? s.evidenceBefore} />
            </div>
          )}
          <Reveal><ProofPanel s={s} /></Reveal>
        </motion.section>

        <motion.section {...section} id="chapter-proof" aria-labelledby="h-report" data-chapter-theme="light" className="chapter-light -mx-4 space-y-3 rounded-3xl px-4 py-8" data-reveal>
          {heading("h-report", "Report")}
          {s.phase === "done" ? <button type="button" className="rounded-md px-4 py-2 font-semibold transition-opacity hover:opacity-90" style={{ background: "var(--accent)", color: "var(--panel)" }} onClick={async () => { const r = await fetch(apiUrl("/api/report"), { headers: { "X-MLDoctor-Token": tokenRef.current } }); if (!r.ok) return; const url = URL.createObjectURL(await r.blob()); const a = document.createElement("a"); a.href = url; a.download = "mldoctor-report.html"; a.click(); URL.revokeObjectURL(url); }}>Download HTML report</button>
            : <p className="text-dim text-sm">Report download appears after a run finishes.</p>}
          <h3 className="font-semibold">Run history (saved in this browser)</h3>
          {s.history.length === 0 ? <p className="text-dim text-sm">No completed runs yet.</p>
            : <ul className="space-y-1 font-mono text-sm">{s.history.map((h, i) => <li key={i} className="rounded border border-line bg-panel px-3 py-2">{new Date(h.at * 1000).toLocaleTimeString()} · {h.script} · {h.verdict} ({h.passed ? "passed" : "not passed"})</li>)}</ul>}
        </motion.section>
      <footer data-chapter-theme="dark" className="chapter-dark -mx-4 mt-4 rounded-t-3xl px-4 py-10 text-center">
          <p className="display-huge">Prove the <span className="font-serif-accent text-[#6f8cff]">fix.</span></p>
          <p className="mt-4 font-mono text-xs text-dim">Built during the Meta Global AI Developer Hackathon · mode: {s.mode ?? "—"}{s.mode === "MOCK" ? " (simulated)" : ""} · MLDoctor web 0.1.0</p>
        </footer>
      </main>
    </div>
  );
}
