"use client";
import { motion, useReducedMotion } from "framer-motion";
import type { State } from "@/lib/reducer";
import { DiffView } from "@/components/charts";
// Light scanner sweeps the diff as real anti-masking checks report.
// Checklist ticks appear per real check (violations / patch events) only.
export default function PatchScanner({ s }: { s: State }) {
  const reduce = useReducedMotion();
  const checks = [
    { label: "Patch proposed by server", ok: s.patch !== null },
    { label: "Patch applied (diff received)", ok: s.diff !== null },
    { label: "Anti-masking gate — no violations", ok: s.diff !== null && s.violations.length === 0, bad: s.violations.length > 0 },
    { label: "Verification completed", ok: s.verdict !== null },
  ];
  return (
    <div className="relative">
      {s.phase === "running" && s.diff && !reduce && (
        <motion.div aria-hidden="true" className="pointer-events-none absolute inset-x-0 z-10 h-10 bg-gradient-to-b from-transparent via-[#2f5bff]/25 to-transparent"
          animate={{ top: ["0%", "92%", "0%"] }} transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }} />
      )}
      <DiffView diff={s.diff} violations={s.violations} />
      <ul className="mt-4 grid gap-2 sm:grid-cols-2" aria-label="Patch checks from server events">
        {checks.map((c) => (
          <li key={c.label} className={`flex items-center gap-2 rounded-lg border px-3 py-2 font-mono text-xs ${c.bad ? "border-[#ff4d5e] text-[#ff4d5e]" : c.ok ? "border-[#2f5bff] text-[#2f5bff]" : "border-line text-dim"}`}>
            <span aria-hidden="true">{c.bad ? "✕" : c.ok ? "✓" : "○"}</span>{c.label}
          </li>
        ))}
      </ul>
      {s.violations.length > 0 && <p className="mt-2 font-mono text-xs text-[#ff4d5e]">REJECTED by anti-masking gate: {s.violations.join("; ")}</p>}
    </div>
  );
}
