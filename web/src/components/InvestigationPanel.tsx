"use client";
import { useMemo, useState } from "react";
import type { State } from "@/lib/reducer";
import { explodedStep } from "@/lib/helpers";

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(4) : String(v);
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

export default function InvestigationPanel({ s }: { s: State }) {
  const [step, setStep] = useState(0);
  const curves = useMemo(() => s.evidenceBefore?.loss_curves ?? [], [s.evidenceBefore]);
  const maxStep = Math.max(0, ...curves.map((c) => c.length - 1));
  const blast = useMemo(() => explodedStep(curves), [curves]);
  const cur = curves.map((c) => (c.length ? c[Math.min(step, c.length - 1)] : null));
  return (
    <section aria-label="Investigation timeline" className="space-y-3">
      <h3 className="label">Investigation — program runs experiments, model only picks the id</h3>
      {s.hypotheses.length > 0 ? (
        <ol className="space-y-1">
          {s.hypotheses.map((h, i) => (
            <li key={h} className="rounded border border-line px-3 py-2 text-sm transition-all">
              <span className="font-mono text-xs text-dim">#{i + 1}</span> {h}
              <span className="ml-2 inline-block h-1.5 rounded bg-tealx align-middle" style={{ width: `${Math.max(20, 90 - i * 18)}%`, opacity: 1 - i * 0.15 }} aria-hidden="true" />
            </li>
          ))}
        </ol>
      ) : <p className="text-dim text-sm">No re-ranking yet — hypotheses arrive from <span className="font-mono">hypotheses_reranked</span> events.</p>}
      {s.activeExperiment ? <p className="font-mono text-xs text-amberx" role="status">Running {s.activeExperiment}…</p> : null}
      <ol className="space-y-1">
        {s.experiments.map((e, i) => (
          <li key={`${e.experiment}-${i}`} className="rounded border border-line px-3 py-2 font-mono text-xs">
            <strong>{String(e.experiment)}</strong> — {Object.entries(e).filter(([k]) => k !== "experiment")
              .map(([k, v]) => `${k}=${fmt(v)}`).join(" · ")}
          </li>
        ))}
      </ol>
      {curves.length > 0 && (
        <div className="space-y-1">
          <label className="text-sm" htmlFor="div-scrub">First-divergence scrubber — step {step}{blast !== null ? ` (explodes near ${blast})` : ""}</label>
          <input id="div-scrub" type="range" min={0} max={Math.max(maxStep, 0)} value={step}
            onChange={(ev) => setStep(Number(ev.target.value))} className="w-full"
            aria-valuetext={`step ${step}, losses ${cur.map((v) => fmt(v)).join(", ")}`} />
          <p className="font-mono text-xs text-dim">{cur.map((v, i) => `run ${i}: ${fmt(v)}`).join(" · ")}</p>
          {blast !== null && step < blast ? <button type="button" className="rounded border border-line px-2 py-1 font-mono text-xs" onClick={() => setStep(blast)}>Jump to step {blast}</button> : null}
        </div>
      )}
      {s.symptom === "leakage" && (
        <div className="rounded border border-line px-3 py-2 text-sm" role="status">
          <strong>Leakage:</strong> overlap {s.leakageBefore ?? "—"} rows before
          {s.leakageAfter !== null ? <> → {s.leakageAfter} after</> : null}
          {s.metricBefore !== null && s.metricAfter !== null
            ? <> · honest metric {s.metricBefore.toFixed(4)} → {s.metricAfter.toFixed(4)} (drop is expected)</>
            : null}
        </div>
      )}
    </section>
  );
}
