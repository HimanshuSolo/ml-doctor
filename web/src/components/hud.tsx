"use client";
import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { State } from "@/lib/reducer";

const STEPS = ["Reproduce", "Classify", "Investigate", "Patch", "Verify"] as const;
export function stepIndex(s: State): number {
  if (s.verdict || s.nTotal > 0) return 4;
  if (s.diff || s.patch) return 3;
  if (s.diagnosis) return 2;
  if (s.symptom) return 1;
  if (s.phase === "running") return 0;
  return -1;
}
export function Hud({ s, conn = "open" }: { s: State; conn?: "connecting" | "open" | "error" }) {
  const active = stepIndex(s);
  const [dark, setDark] = useState(false);
  useEffect(() => {
    let saved: string | null = null;
    try { saved = localStorage.getItem("mldoctor-theme"); } catch { /* storage unavailable */ }
    if (saved === "dark") { document.documentElement.dataset.theme = "dark"; const t = setTimeout(() => setDark(true), 0); return () => clearTimeout(t); }
  }, []);
  function toggle() {
    const next = !dark;
    setDark(next);
    if (next) document.documentElement.dataset.theme = "dark"; else document.documentElement.removeAttribute("data-theme");
    try { localStorage.setItem("mldoctor-theme", next ? "dark" : "light"); } catch { /* ignore */ }
  }
  return (
    <header className="themed-chrome sticky top-0 z-50 border-b border-line shadow-[0_1px_0_rgba(24,36,32,0.04),0_10px_30px_-18px_rgba(24,36,32,0.35)]" style={{ background: "var(--panel)" }}>
      <div className="mx-auto max-w-6xl px-4">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
          <strong className="flex items-center gap-2 tracking-tight">
            <span aria-hidden="true" className="grid h-6 w-6 place-items-center rounded-md text-xs text-white" style={{ background: "var(--accent)" }}>M</span>
            MLDoctor
          </strong>
          <button type="button" onClick={toggle} aria-pressed={dark} className="shrink-0 rounded-full border border-line px-3 py-1 font-mono text-xs text-dim transition-colors hover:text-ink xl:ml-0">{dark ? "☀ Light" : "☾ Dark"}</button>
          <span aria-label="Server mode" className={`rounded border px-2 py-0.5 font-mono text-xs ${s.mode === "LIVE" ? "border-amberx text-amberx" : s.mode === "MOCK" ? "border-tealx text-tealx" : "border-line text-dim"}`}>{s.mode ?? "MODE —"}</span>
          <span aria-label="Event stream connection" role="status" className={`rounded border px-2 py-0.5 font-mono text-xs ${conn === "open" ? "border-tealx text-tealx" : conn === "error" ? "border-redx text-redx" : "border-line text-dim"}`}>{conn === "open" ? "● SSE connected" : conn === "error" ? "● SSE disconnected" : "● SSE connecting…"}</span>
          {s.demoPacing && <span className="rounded border border-amberx px-2 py-0.5 font-mono text-xs text-amberx">DEMO PACING</span>}
          <span className="font-mono text-xs text-dim">calls: {s.llmCalls ?? "—"}{s.callCap ? ` / ${s.callCap}` : ""} · tokens: {s.tokensUsed ?? "—"}</span>
          <span className="font-mono text-xs" aria-label="Verification counter">verify: {s.nDone} / {s.nTotal}{s.nFailed ? ` (${s.nFailed} failed)` : ""}</span>
          <span className={`font-mono text-xs ${s.verdict === "PASS" ? "text-greenx" : s.verdict === "FAIL" ? "text-redx" : "text-dim"}`}>{s.verdict ? `verdict: ${s.verdict}` : "verdict: —"}</span>
          <nav aria-label="Pipeline" className="ml-auto hidden xl:block">
            <ol className="flex gap-1">
              {STEPS.map((label, i) => (
                <li key={label} aria-current={i === active ? "step" : undefined}
                  className={`rounded px-2 py-1 text-xs ${i === active ? "bg-tealx/15 text-tealx outline outline-1 outline-tealx" : i < active ? "text-tealx" : "text-dim"}`}>
                  {i < active ? "✓ " : i === active ? "● " : "○ "}{label}</li>
              ))}
            </ol>
          </nav>
        </div>
      </div>
    </header>
  );
}
export function Odometer({ value, total }: { value: number; total: number }) {
  const reduceMotion = useReducedMotion();
  return (
    <div className="flex items-center gap-3" aria-label={`Verified ${value} of ${total}`}>
      <div className="flex overflow-hidden rounded-md border border-line bg-panel2 font-mono text-4xl" aria-hidden="true">
        {String(value).padStart(2, "0").split("").map((d, i) => (
          <motion.span key={`${i}-${d}`} initial={reduceMotion ? false : { y: 18, opacity: 1 }} animate={{ y: 0, opacity: 1 }} className="px-2 py-1">{d}</motion.span>
        ))}
      </div>
      <span className="font-mono text-xl text-dim">/ {total || "—"}</span>
    </div>
  );
}
export function EventLog({ s }: { s: State }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open && ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [s.events, open]);
  return (
    <section aria-label="Event log" className="rounded-lg border border-line bg-panel2 p-4">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="label underline-offset-2 hover:underline">{open ? "▾" : "▸"} Event log · {s.events.length}</button>
      {open && <div ref={ref} tabIndex={0} className="mt-2 max-h-56 overflow-y-auto font-mono text-xs leading-5 text-dim">
        {s.events.length === 0 ? <p>No server events yet.</p> : s.events.map((e) => <div key={e.seq}><span className="text-tealx">[{new Date(e.ts * 1000).toLocaleTimeString()}]</span> #{e.seq} {e.type}</div>)}
      </div>}
    </section>
  );
}
