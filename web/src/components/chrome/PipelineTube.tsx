"use client";
import type { State } from "@/lib/reducer";
import { stepIndex } from "@/components/hud";
const STATIONS = ["Reproduce", "Classify", "Investigate", "Patch", "Verify"] as const;
// Luminous pipeline tube: packet + lit stations come ONLY from real step
// events via stepIndex(state). Failed/rejected steps get a deliberate state.
export default function PipelineTube({ s }: { s: State }) {
  const active = stepIndex(s);
  const failed = s.phase === "failed" || s.verdict === "FAIL";
  const pct = active < 0 ? 0 : ((active + 0.5) / STATIONS.length) * 100;
  return (
    <div aria-label="Pipeline progress from server events">
      <div className="relative mx-2 my-10 h-[6px] rounded-full bg-line">
        <div className="absolute inset-y-0 left-0 rounded-full bg-[#bc4a1a] transition-all duration-700" style={{ width: `${active < 0 ? 0 : pct}%` }} />
        {active >= 0 && (
          <div aria-hidden="true" className={`absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-[0_0_24px_#bc4a1a] transition-all duration-700 ${failed && active === 4 ? "bg-[#ff4d5e]" : "bg-[#bc4a1a]"} ${s.phase === "running" ? "animate-pulse" : ""}`} style={{ left: `${pct}%` }} />
        )}
        {s.phase === "running" && <div aria-hidden="true" className="absolute -top-4 font-mono text-[10px] text-[#ff8a5f]" style={{ left: `calc(${pct}% - 30px)` }}>▼ SCANNING</div>}
      </div>
      <ol className="grid grid-cols-5 gap-1 text-center">
        {STATIONS.map((name, i) => {
          const lit = i < active || s.phase === "done";
          const cur = i === active;
          const bad = failed && cur;
          return (
            <li key={name} aria-current={cur ? "step" : undefined} className={`rounded-lg border px-1 py-3 transition-all duration-500 ${bad ? "border-[#ff4d5e] bg-[#ff4d5e]/10 text-[#ff4d5e]" : cur ? "border-[#bc4a1a] bg-[#bc4a1a]/10 shadow-[0_0_28px_rgba(188,74,26,0.35)]" : lit ? "border-[#bc4a1a]/50" : "border-line opacity-55"}`}>
              <span className="block font-mono text-[10px] tracking-widest">{bad ? "✕ REJECTED" : cur ? "● ACTIVE" : lit ? "✓ DONE" : "○ WAITING"}</span>
              <span className="mt-1 block text-sm font-semibold sm:text-base">{name}</span>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-center font-mono text-xs text-dim">{active < 0 ? "No step yet — stations light only on real server events." : `Station ${active + 1}/5 from server events · ${s.events.length} events received`}</p>
    </div>
  );
}
