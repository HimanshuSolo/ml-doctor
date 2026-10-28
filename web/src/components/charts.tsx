"use client";
import type { Evidence } from "@/lib/events";
import { explodedStep, hashColor, parseDiff } from "@/lib/helpers";
import type { RunDatum } from "@/lib/events";

export function LossChart({ evidence, title }: { evidence: Evidence | null; title: string }) {
  if (!evidence?.loss_curves?.length) return <p className="text-dim text-sm">No telemetry yet — this fills only when the server sends it.</p>;
  const flat = evidence.loss_curves.flat().filter((v): v is number => v !== null && Number.isFinite(v));
  const max = Math.max(...flat, 1), min = Math.min(...flat, 0), W = 560, H = 180;
  const boom = explodedStep(evidence.loss_curves);
  const maxLen = Math.max(...evidence.loss_curves.map((c) => c.length), 1);
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded border border-line bg-panel2" role="img" aria-label={title}>
        {evidence.loss_curves.map((c, i) => (
          <polyline key={i} className="loss-line" fill="none" stroke={`hsl(${190 + i * 28} 85% 62%)`} strokeWidth="2"
            points={c.map((y, j) => `${(j / Math.max(maxLen - 1, 1)) * W},${y === null || !Number.isFinite(y) ? H : H - ((y - min) / Math.max(max - min, 1e-9)) * (H - 12) - 6}`).join(" ")} />
        ))}
        {boom !== null && <g><line x1={(boom / Math.max(maxLen - 1, 1)) * W} y1="0" x2={(boom / Math.max(maxLen - 1, 1)) * W} y2={H} stroke="#f87171" strokeDasharray="4 3" /><text x={Math.min((boom / Math.max(maxLen - 1, 1)) * W + 6, W - 150)} y="16" fill="#f87171" fontSize="12">exploded at step {boom}</text></g>}
      </svg>
      <figcaption className="mt-1 font-mono text-xs text-dim">{title}: {evidence.loss_curves.length} run(s){boom !== null ? ` · diverged at step ${boom}` : ""}</figcaption>
    </figure>
  );
}

export function HashCells({ evidence, title }: { evidence: Evidence | null; title: string }) {
  if (!evidence?.hash_fingerprints?.length) return <p className="text-dim text-sm">No hash fingerprints yet.</p>;
  return (
    <div>
      <h3 className="mb-2 font-mono text-xs text-dim">{title}</h3>
      <div className="space-y-1">
        {evidence.hash_fingerprints.map((run, i) => (
          <div key={i} className="flex flex-wrap items-center gap-1">
            <span className="w-14 font-mono text-xs text-dim">run {i}</span>
            {run.map((h, j) => <span key={j} title={`run ${i} step ${j}: ${h}`} className="rounded px-1.5 py-0.5 font-mono text-[11px] text-black" style={{ background: hashColor(h) }}>{h}</span>)}
          </div>
        ))}
      </div>
      <p className="mt-1 text-xs text-dim">Colour is derived from the hash value itself. Matching colours + text across runs = identical hashes.</p>
    </div>
  );
}

const BAD = new Set(["different", "diverged", "error"]);
export function RunGrid({ nDone, nTotal, nFailed, runs, verdict }: { nDone: number; nTotal: number; nFailed: number; runs: RunDatum[]; verdict: string | null }) {
  if (!nTotal) return <p className="text-dim text-sm">Verification has not started. No runs to show.</p>;
  return (
    <div>
      <div className="grid grid-cols-5 gap-2 sm:grid-cols-10" role="list" aria-label="Verification runs">
        {Array.from({ length: nTotal }, (_, i) => {
          const run = runs[i] as RunDatum | undefined;
          if (!run) return <div key={i} role="listitem" className="rounded border border-line bg-panel2 p-2 text-center font-mono text-xs text-dim">{i + 1}<br />awaiting event</div>;
          const bad = BAD.has(run.status);
          const cls = bad || (verdict === "FAIL" && bad) ? "border-redx text-redx" : verdict === "PASS" && !bad ? "border-greenx text-greenx" : "border-tealx text-tealx";
          return (
            <div key={i} role="listitem" tabIndex={0} title={`run ${i}: ${run.status}, peak loss ${run.peak_loss ?? "—"}, final loss ${run.final_loss ?? "—"}`}
              className={`rounded border bg-panel2 p-2 text-center font-mono text-xs ${cls}`}>
              {i + 1} · {run.status}{bad ? " ✗" : verdict === "PASS" ? " ✓" : ""}
              <span className="mt-1 block rounded px-1 text-black" style={{ background: run.param_hash ? hashColor(run.param_hash) : "#334155" }}>{run.param_hash ?? "no hash"}</span>
              <span className="mt-1 block text-[10px] text-dim">peak {run.peak_loss?.toFixed(3) ?? "—"}</span>
            </div>
          );
        })}
      </div>
      <p className="mt-2 font-mono text-sm">{nDone} / {nTotal} done · {nFailed} failed (server-reported) · cell colour from the run&apos;s real hash</p>
    </div>
  );
}

export function DiffView({ diff, violations }: { diff: string | null; violations: string[] }) {
  if (!diff) return <p className="text-dim text-sm">No patch yet.</p>;
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      <pre className="overflow-x-auto rounded border border-line bg-panel2 p-3 font-mono text-xs leading-5" tabIndex={0} aria-label="Unified diff">
        {parseDiff(diff).map((l, i) => <div key={i} className={l.kind === "add" ? "bg-tealx/15 text-tealx" : l.kind === "del" ? "bg-redx/15 text-redx" : "text-dim"}>{l.text || " "}</div>)}
      </pre>
      <aside className="rounded border border-line bg-panel2 p-3" aria-label="Anti-masking checks">
        <h3 className="font-semibold">Anti-masking gate</h3>
        {violations.length ? <ul className="mt-2 list-disc pl-5 text-sm text-redx">{violations.map((v) => <li key={v}>REJECTED: {v}</li>)}</ul>
          : <p className="mt-2 text-sm text-dim">No violations reported by the server for this patch. (The gate also checks epochs, dataset, model, try/except, loss masking, hardcoded metrics and weakened asserts.)</p>}
      </aside>
    </div>
  );
}
