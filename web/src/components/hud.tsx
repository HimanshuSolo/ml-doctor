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
export function Hud({ s }: { s: State }) {
  const active = stepIndex(s);
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-abyss/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2">
        <strong className="text-lg tracking-tight">MLDoctor</strong>
        <span aria-label="Server mode" className={`rounded border px-2 py-0.5 font-mono text-xs ${s.mode === "LIVE" ? "border-amberx text-amberx" : s.mode === "MOCK" ? "border-bluex text-bluex" : "border-line text-dim"}`}>{s.mode ?? "MODE —"}</span>
        {s.demoPacing && <span className="rounded border border-amberx px-2 py-0.5 font-mono text-xs text-amberx">DEMO PACING</span>}
        <span className="font-mono text-xs text-dim">calls: {s.llmCalls ?? "—"}{s.callCap ? ` / ${s.callCap}` : ""} · tokens: {s.tokensUsed ?? "—"}</span>
        <span className="font-mono text-xs" aria-label="Verification counter">verify: {s.nDone} / {s.nTotal}{s.nFailed ? ` (${s.nFailed} failed)` : ""}</span>
        <span className={`font-mono text-xs ${s.verdict === "PASS" ? "text-greenx" : s.verdict === "FAIL" ? "text-redx" : "text-dim"}`}>{s.verdict ? `verdict: ${s.verdict}` : "verdict: —"}</span>
        <nav aria-label="Pipeline" className="ml-auto">
          <ol className="flex gap-1">
            {STEPS.map((label, i) => (
              <li key={label} aria-current={i === active ? "step" : undefined}
                className={`rounded px-2 py-1 text-xs ${i === active ? "bg-bluex/20 text-bluex outline outline-1 outline-bluex" : i < active ? "text-tealx" : "text-dim"}`}>
                {i < active ? "✓ " : i === active ? "● " : "○ "}{label}</li>
            ))}
          </ol>
        </nav>
      </div>
    </header>
  );
}
export function Odometer({ value, total }: { value: number; total: number }) {
  const reduceMotion = useReducedMotion();
  return (
    <div className="flex items-center gap-3" aria-label={`Verified ${value} of ${total}`}>
      <div className="flex overflow-hidden rounded border border-line bg-panel2 font-mono text-4xl" aria-hidden="true">
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
    <section aria-label="Event log" className="rounded border border-line bg-panel p-4">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="font-semibold underline-offset-2 hover:underline">{open ? "▾" : "▸"} Event log ({s.events.length})</button>
      {open && <div ref={ref} tabIndex={0} className="mt-2 max-h-56 overflow-y-auto font-mono text-xs leading-5">
        {s.events.length === 0 ? <p className="text-dim">No server events yet.</p> : s.events.map((e) => <div key={e.seq}>[{new Date(e.ts * 1000).toLocaleTimeString()}] #{e.seq} {e.type}</div>)}
      </div>}
    </section>
  );
}
